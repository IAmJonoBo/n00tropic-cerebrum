const form = document.getElementById("upload-form");
const logEl = document.getElementById("log");

function log(text) {
  logEl.textContent = text;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById("file");
  const dataset = document.getElementById("dataset").value.trim();
  const backend = document.getElementById("backend").value;
  if (!fileInput.files.length) {
    log("Select a PDF first.");
    return;
  }
  const file = fileInput.files[0];
  const formData = new FormData();
  formData.append("pdf", file);
  if (dataset) formData.append("dataset", dataset);
  if (backend) formData.append("backend", backend);
  log("Uploading and processing…");
  try {
    const res = await fetch("/upload", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || res.statusText);
    }
    const assets = data.assets || [];
    const lines = [
      `Status: ${data.status}`,
      data.output || "",
      data.dataset ? `Dataset: ${data.dataset}` : "",
      "Assets:",
      ...(assets.length
        ? assets.map((a) => `- ${new URL(a, window.location.href).href}`)
        : ["- n/a"]),
    ].filter(Boolean);
    log(lines.join("\n"));
    if (data.dataset) {
      pollStatus(data.dataset);
    }
  } catch (err) {
    log(`Error: ${err.message}`);
  }
});

async function pollStatus(dataset) {
  logEl.textContent += `\nPolling for assets for ${dataset}...`;
  const start = Date.now();
  const deadline = start + 60_000; // 60 seconds
  const seen = new Set();
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/status?dataset=${encodeURIComponent(dataset)}`);
      const data = await res.json();
      const assets = data.assets || [];
      const newOnes = assets.filter((a) => !seen.has(a));
      newOnes.forEach((a) => seen.add(a));
      if (newOnes.length > 0) {
        logEl.textContent += `\nNew assets:\n${newOnes.map((a) => `- ${new URL(a, window.location.href).href}`).join("\n")}`;
      }
      if (assets.length > 0 || Date.now() > deadline) {
        clearInterval(interval);
      }
    } catch (err) {
      clearInterval(interval);
      logEl.textContent += `\nStatus polling error: ${err.message}`;
    }
  }, 3000);
}
