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
  } catch (err) {
    log(`Error: ${err.message}`);
  }
});
