const pad = document.getElementById("pad");
const ctx = pad.getContext("2d");
const brush = document.getElementById("brush");
const status = document.getElementById("draw-status");

function reset() {
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, pad.width, pad.height);
}
reset();

ctx.lineCap = "round";
ctx.lineJoin = "round";
ctx.strokeStyle = "#000";

let drawing = false;
let last = null;

function pos(e) {
  const rect = pad.getBoundingClientRect();
  const scaleX = pad.width / rect.width;
  const scaleY = pad.height / rect.height;
  const p = e.touches ? e.touches[0] : e;
  return { x: (p.clientX - rect.left) * scaleX, y: (p.clientY - rect.top) * scaleY };
}

function start(e) { drawing = true; last = pos(e); e.preventDefault(); }
function move(e) {
  if (!drawing) return;
  const p = pos(e);
  ctx.lineWidth = parseInt(brush.value, 10);
  ctx.beginPath();
  ctx.moveTo(last.x, last.y);
  ctx.lineTo(p.x, p.y);
  ctx.stroke();
  last = p;
  e.preventDefault();
}
function end() { drawing = false; }

pad.addEventListener("mousedown", start);
pad.addEventListener("mousemove", move);
window.addEventListener("mouseup", end);
pad.addEventListener("touchstart", start);
pad.addEventListener("touchmove", move);
pad.addEventListener("touchend", end);

document.getElementById("clear").onclick = reset;

document.getElementById("push").onclick = async () => {
  status.textContent = "Pushing…";
  try {
    const r = await fetch("/api/draw/push", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image: pad.toDataURL("image/png"),
        device_id: localStorage.getItem("activeDevice") || "",
      }),
    });
    const data = await r.json();
    status.textContent = r.ok ? "On display ✓" : "Failed: " + (data.error || "");
  } catch (e) {
    status.textContent = "Failed: " + e.message;
  }
};
