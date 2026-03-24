const http = require("http");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const root = __dirname;
const port = 4173;
const browserPath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const outputPath = path.join(root, "SDDF_Final_Report.pdf");

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".jsx": "text/plain; charset=utf-8",
};

function startServer() {
  const server = http.createServer((req, res) => {
    const rawPath = req.url === "/" ? "/preview_sddf_combined_paper.html" : req.url;
    const cleanPath = decodeURIComponent(rawPath.split("?")[0]);
    const filePath = path.normalize(path.join(root, cleanPath));

    if (!filePath.startsWith(root)) {
      res.writeHead(403);
      res.end("Forbidden");
      return;
    }

    fs.readFile(filePath, (err, data) => {
      if (err) {
        res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
        res.end("Not found");
        return;
      }

      const ext = path.extname(filePath).toLowerCase();
      res.writeHead(200, {
        "Content-Type": mimeTypes[ext] || "application/octet-stream",
        "Cache-Control": "no-store",
      });
      res.end(data);
    });
  });

  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => resolve(server));
  });
}

function buildPdf() {
  return new Promise((resolve, reject) => {
    const browser = spawn(
      browserPath,
      [
        "--headless=new",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=20000",
        `--print-to-pdf=${outputPath}`,
        `http://127.0.0.1:${port}/`,
      ],
      { cwd: root, stdio: ["ignore", "pipe", "pipe"], windowsHide: true }
    );

    let stderr = "";
    let stdout = "";

    browser.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });

    browser.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    browser.on("exit", (code) => {
      if (code === 0 && fs.existsSync(outputPath)) {
        resolve({ stdout, stderr });
      } else {
        reject(new Error(stderr || stdout || `Chrome exited with code ${code}`));
      }
    });
  });
}

async function main() {
  const server = await startServer();
  try {
    await buildPdf();
    console.log(outputPath);
  } finally {
    server.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
