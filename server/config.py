"""Configuration loader for the Mac-side orchestrator.

Reads config.yaml from the repo root, with environment variables taking
precedence for secrets (so you can keep keys out of the file if you prefer).
"""

import os
from dataclasses import dataclass, field

import yaml

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_PATH = os.path.join(_REPO_ROOT, "config.yaml")


@dataclass
class LLMConfig:
    anthropic_api_key: str = ""
    model: str = "claude-sonnet-4-6"


@dataclass
class ImageGenConfig:
    provider: str = "replicate"
    replicate_api_token: str = ""
    model: str = "black-forest-labs/flux-schnell"


@dataclass
class DeviceConfig:
    discovery: str = "mdns"
    fallback_host: str = "koipond.local"
    fallback_port: int = 8080


@dataclass
class RenderConfig:
    resolution: tuple = (648, 480)
    dither: str = "floyd-steinberg"  # or "threshold"


@dataclass
class AuthConfig:
    password: str = ""  # empty => no gate


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    image_gen: ImageGenConfig = field(default_factory=ImageGenConfig)
    device: DeviceConfig = field(default_factory=DeviceConfig)
    render: RenderConfig = field(default_factory=RenderConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)

    @classmethod
    def load(cls) -> "Config":
        data = {}
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH) as f:
                data = yaml.safe_load(f) or {}

        llm = data.get("llm", {})
        image_gen = data.get("image_gen", {})
        device = data.get("device", {})
        render = data.get("render", {})
        auth = data.get("auth", {})

        res = render.get("resolution", [648, 480])

        return cls(
            llm=LLMConfig(
                anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or llm.get("anthropic_api_key", ""),
                model=llm.get("model", "claude-sonnet-4-6"),
            ),
            image_gen=ImageGenConfig(
                provider=image_gen.get("provider", "replicate"),
                replicate_api_token=os.environ.get("REPLICATE_API_TOKEN") or image_gen.get("replicate_api_token", ""),
                model=image_gen.get("model", "black-forest-labs/flux-schnell"),
            ),
            device=DeviceConfig(
                discovery=device.get("discovery", "mdns"),
                fallback_host=device.get("fallback_host", "koipond.local"),
                fallback_port=int(device.get("fallback_port", 8080)),
            ),
            render=RenderConfig(
                resolution=(int(res[0]), int(res[1])),
                dither=render.get("dither", "floyd-steinberg"),
            ),
            auth=AuthConfig(
                password=os.environ.get("EINK_PASSWORD") or auth.get("password", ""),
            ),
        )
