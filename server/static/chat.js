const messages = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("chat-input");
const sessionId = "s-" + Math.random().toString(36).slice(2, 10);

function activeDevice() {
  return localStorage.getItem("activeDevice") || "";
}

function addMessage(text, role) {
  const wrap = document.createElement("div");
  wrap.className = "msg " + role;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  wrap.appendChild(bubble);
  messages.appendChild(wrap);
  messages.scrollTop = messages.scrollHeight;
  return bubble;
}

function addGenerated(image) {
  const card = document.createElement("div");
  card.className = "gen";

  const img = document.createElement("img");
  img.src = image.preview_url;
  card.appendChild(img);

  const btn = document.createElement("button");
  btn.className = "primary";
  btn.textContent = "Push to display";
  btn.onclick = async () => {
    btn.disabled = true;
    btn.textContent = "Pushing…";
    try {
      const r = await fetch("/api/push", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_id: image.id, device_id: activeDevice() }),
      });
      const data = await r.json();
      btn.textContent = r.ok ? "On display ✓" : "Failed: " + (data.error || "");
    } catch (e) {
      btn.textContent = "Failed";
    }
  };
  card.appendChild(btn);

  const last = messages.querySelector(".msg.assistant:last-child .bubble");
  (last || messages).appendChild(card);
  messages.scrollTop = messages.scrollHeight;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  addMessage(text, "user");
  input.value = "";

  const thinking = addMessage("…", "assistant");
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    });
    const data = await r.json();
    thinking.textContent = data.reply || data.error || "(no response)";
    (data.images || []).forEach(addGenerated);
  } catch (err) {
    thinking.textContent = "Error: " + err.message;
  }
});
