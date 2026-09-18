const list = document.getElementById("device-list");
const refresh = document.getElementById("refresh");

function activeDevice() {
  return localStorage.getItem("activeDevice") || "";
}

async function load() {
  list.innerHTML = '<li class="muted">Scanning…</li>';
  let devices = [];
  try {
    const r = await fetch("/api/devices");
    devices = (await r.json()).devices || [];
  } catch (e) {
    list.innerHTML = '<li class="muted">Failed to scan.</li>';
    return;
  }

  if (!devices.length) {
    list.innerHTML = '<li class="muted">No devices found.</li>';
    return;
  }

  list.innerHTML = "";
  devices.forEach((d) => {
    const li = document.createElement("li");
    if (d.device_id === activeDevice()) li.classList.add("active");

    const dot = document.createElement("span");
    dot.className = "dot " + (d.online ? "online" : "offline");
    li.appendChild(dot);

    const label = document.createElement("div");
    label.innerHTML = `<strong>${d.name}</strong><br><span class="muted">${d.host}:${d.port}</span>`;
    li.appendChild(label);

    const btn = document.createElement("button");
    btn.className = "ghost pick";
    btn.textContent = d.device_id === activeDevice() ? "Active" : "Set active";
    btn.onclick = () => {
      localStorage.setItem("activeDevice", d.device_id);
      load();
    };
    li.appendChild(btn);
    list.appendChild(li);
  });
}

refresh.addEventListener("click", load);
load();
