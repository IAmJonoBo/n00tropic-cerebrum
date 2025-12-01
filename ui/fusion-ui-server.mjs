#!/usr/bin/env node
import * as fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import Busboy from "busboy";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const fusionDir = path.join(root, "n00clear-fusion");
const pipelineScript = path.join(
  root,
  ".dev",
  "automation",
  "scripts",
  "fusion-pipeline.sh",
);

function serveStatic(req, res) {
  const url = req.url === "/" ? "/index.html" : req.url;
  const filePath = path.join(__dirname, url);
  if (!fs.existsSync(filePath)) return false;
  const content = fs.readFileSync(filePath);
  const type = filePath.endsWith(".js")
    ? "application/javascript"
    : "text/html";
  res.writeHead(200, { "Content-Type": type });
  res.end(content);
  return true;
}

function serveExport(req, res) {
  if (!req.url.startsWith("/exports/")) return false;
  const target = path.join(root, req.url);
  if (!fs.existsSync(target)) return false;
  const content = fs.readFileSync(target);
  res.writeHead(200, { "Content-Type": "text/plain" });
  res.end(content);
  return true;
}

function serveStatus(req, res) {
  const url = new URL(req.url, "http://localhost");
  if (url.pathname !== "/status") return false;
  const dataset = url.searchParams.get("dataset");
  if (!dataset) {
    res.writeHead(400, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "dataset required" }));
    return true;
  }
  const genDir = path.join(fusionDir, "exports", dataset, "generated");
  let assets = [];
  if (fs.existsSync(genDir)) {
    assets = fs
      .readdirSync(genDir)
      .map((name) => path.join("exports", dataset, "generated", name));
  }
  res.writeHead(200, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ dataset, assets }));
  return true;
}

function handleUpload(req, res) {
  const busboy = Busboy({ headers: req.headers });
  const uploadsDir = path.join(fusionDir, "corpora");
  fs.mkdirSync(uploadsDir, { recursive: true });
  let dataset = "";
  let filePath = "";
  let backend = "";
  busboy.on("file", (_name, file, info) => {
    const saveTo = path.join(uploadsDir, info.filename);
    filePath = saveTo;
    file.pipe(fs.createWriteStream(saveTo));
  });
  busboy.on("field", (name, val) => {
    if (name === "dataset") dataset = val;
    if (name === "backend") backend = val;
  });
  busboy.on("close", () => {
    if (!filePath) {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "No file uploaded" }));
      return;
    }
    const args = [pipelineScript, filePath];
    if (dataset) args.push(dataset);
    const env = { ...process.env };
    if (backend) env["FUSION_EMBED_BACKEND"] = backend;
    const proc = spawn("bash", args.slice(0), { cwd: root, env });
    let output = "";
    let assets = [];
    let resultDataset = dataset;
    proc.stdout.on("data", (d) => {
      output += d.toString();
    });
    proc.stderr.on("data", (d) => {
      output += d.toString();
    });
    proc.on("close", (code) => {
      const status = code === 0 ? "ok" : "error";
      // naive asset extraction
      const matchLine = output
        .split("\n")
        .find((line) => line.startsWith("PIPELINE_RESULT"));
      if (matchLine) {
        const parts = Object.fromEntries(
          matchLine
            .replace("PIPELINE_RESULT", "")
            .trim()
            .split(" ")
            .map((kv) => kv.split("=")),
        );
        resultDataset = parts.dataset || resultDataset;
        assets = parts.assets ? parts.assets.split(",").filter(Boolean) : [];
      } else {
        assets = output.match(/generated\/[^\s]+/g) || [];
      }
      // Best-effort list from filesystem when dataset is known
      if (resultDataset) {
        const genDir = path.join(
          fusionDir,
          "exports",
          resultDataset,
          "generated",
        );
        if (fs.existsSync(genDir)) {
          const found = fs
            .readdirSync(genDir)
            .map((name) =>
              path.join("exports", resultDataset, "generated", name),
            );
          assets = assets.concat(found);
        }
      }

      res.writeHead(code === 0 ? 200 : 500, {
        "Content-Type": "application/json",
      });
      res.end(
        JSON.stringify({
          status,
          output,
          assets,
          dataset: resultDataset,
        }),
      );
    });
  });
  req.pipe(busboy);
}

const server = http.createServer((req, res) => {
  if (req.method === "POST" && req.url === "/upload") {
    return handleUpload(req, res);
  }
  if (req.method === "GET" && req.url.startsWith("/status")) {
    return serveStatus(req, res);
  }
  if (serveExport(req, res)) {
    return;
  }
  if (!serveStatic(req, res)) {
    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "not found" }));
  }
});

const port = process.env.FUSION_UI_PORT || 7800;
server.listen(port, () => {
  console.log(`[fusion-ui] listening on http://localhost:${port}`);
});
