"""Claude chat loop with tool calling.

Runs a manual agentic loop (per the Anthropic tool-use docs) so we have full
control: when Claude calls generate_static_image, we run Flux, save the result,
track it for the UI, and feed a short confirmation back to the model.

The generated image bytes never go through Claude — only a reference does. The
Flask layer serves previews and handles the "push to display" action.
"""

import logging
import uuid

import anthropic

from server import pipeline
from server.tools import image_static

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You help a user create images for a 648x480 1-bit (black and white) \
e-ink display. When the user describes something they want to see on the display, \
call the generate_static_image tool with a vivid, concrete prompt. Favor bold, \
high-contrast compositions with clear subjects, since the image will be dithered to \
pure black and white. After generating, briefly describe what you made in one sentence \
and remind the user they can push it to the display. Keep replies short and friendly."""

TOOLS = [
    {
        "name": "generate_static_image",
        "description": (
            "Generate a single static image from a text prompt and show it to the user "
            "as a preview. Use this whenever the user asks to create, draw, generate, or "
            "see an image. The prompt should be a vivid, concrete visual description."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A vivid, concrete visual description of the image to generate.",
                }
            },
            "required": ["prompt"],
        },
    }
]


class Orchestrator:
    def __init__(self, config, image_store):
        self.config = config
        self.image_store = image_store  # dict: image_id -> {"image": PIL, "preview": PIL, "prompt": str}
        self.client = anthropic.Anthropic(api_key=config.llm.anthropic_api_key)
        self.sessions = {}  # session_id -> message history

    def _run_tool(self, name, tool_input):
        """Execute a tool call. Returns (result_text, generated_image_id_or_None)."""
        if name != "generate_static_image":
            return f"Unknown tool: {name}", None

        prompt = tool_input.get("prompt", "").strip()
        if not prompt:
            return "Error: empty prompt.", None

        try:
            rgb = image_static.generate(
                prompt,
                api_token=self.config.image_gen.replicate_api_token,
                model=self.config.image_gen.model,
            )
        except Exception as e:  # noqa: BLE001 - report failures back to the model
            logger.exception("image generation failed")
            return f"Image generation failed: {e}", None

        preview = pipeline.to_epaper(
            rgb,
            size=self.config.render.resolution,
            dither=self.config.render.dither,
        )
        image_id = uuid.uuid4().hex[:12]
        self.image_store[image_id] = {"image": rgb, "preview": preview, "prompt": prompt}
        return f"Image generated successfully (id: {image_id}).", image_id

    def chat(self, session_id, user_message):
        """Process a user message. Returns {"reply": str, "images": [image_id, ...]}."""
        history = self.sessions.setdefault(session_id, [])
        history.append({"role": "user", "content": user_message})

        generated = []

        while True:
            response = self.client.messages.create(
                model=self.config.llm.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=history,
            )
            history.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                break

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result_text, image_id = self._run_tool(block.name, block.input)
                if image_id:
                    generated.append(image_id)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })
            history.append({"role": "user", "content": tool_results})

        reply = "".join(b.text for b in response.content if b.type == "text")
        return {"reply": reply, "images": generated}
