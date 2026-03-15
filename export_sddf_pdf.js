const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const browserPath = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const workdir = __dirname;
const url = "http://127.0.0.1:4173/";
const outputPath = path.join(workdir, "SDDF_Final_Report.pdf");
const debugPort = 9222;
const userDataDir = path.join(workdir, ".edge-cdp-profile");

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForJsonList(retries = 40) {
  for (let i = 0; i < retries; i += 1) {
    try {
      const res = await fetch(`http://127.0.0.1:${debugPort}/json/list`);
      if (res.ok) {
        const pages = await res.json();
        if (pages.length) return pages;
      }
    } catch {}
    await sleep(500);
  }
  throw new Error("DevTools endpoint did not become ready.");
}

async function exportPdf() {
  fs.mkdirSync(userDataDir, { recursive: true });

  const browser = spawn(
    browserPath,
    [
      `--remote-debugging-port=${debugPort}`,
      `--user-data-dir=${userDataDir}`,
      "--headless=new",
      "--disable-gpu",
      "--no-first-run",
      "--no-default-browser-check",
      url,
    ],
    {
      cwd: workdir,
      stdio: "ignore",
      windowsHide: true,
    }
  );

  try {
    const pages = await waitForJsonList();
    const page = pages.find((p) => p.type === "page") || pages[0];
    const ws = new WebSocket(page.webSocketDebuggerUrl);

    const send = (() => {
      let id = 0;
      const pending = new Map();

      ws.addEventListener("message", (event) => {
        const msg = JSON.parse(event.data);
        if (msg.id && pending.has(msg.id)) {
          const { resolve, reject } = pending.get(msg.id);
          pending.delete(msg.id);
          if (msg.error) reject(new Error(msg.error.message));
          else resolve(msg.result);
        }
      });

      return (method, params = {}) =>
        new Promise((resolve, reject) => {
          id += 1;
          pending.set(id, { resolve, reject });
          ws.send(JSON.stringify({ id, method, params }));
        });
    })();

    await new Promise((resolve, reject) => {
      ws.addEventListener("open", resolve, { once: true });
      ws.addEventListener("error", reject, { once: true });
    });

    await send("Page.enable");
    await send("Runtime.enable");
    await send("Page.navigate", { url });
    await sleep(7000);

    const pdf = await send("Page.printToPDF", {
      printBackground: true,
      preferCSSPageSize: true,
      marginTop: 0.4,
      marginBottom: 0.4,
      marginLeft: 0.35,
      marginRight: 0.35,
    });

    fs.writeFileSync(outputPath, Buffer.from(pdf.data, "base64"));
    ws.close();
    console.log(outputPath);
  } finally {
    browser.kill();
  }
}

exportPdf().catch((error) => {
  console.error(error);
  process.exit(1);
});
