#!/usr/bin/env node
"use strict";

// Isolated browser fixture for RouterCloud Home AJAX.
// Uses only the static Metro preview in /tmp; never contacts cloud.home.arpa.
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

const HOST = "127.0.0.1";
const PORT = 8766;
const PREVIEW = "/tmp/routercloud-metro-preview";

const htmlPath = path.join(PREVIEW, "index.html");
if (!fs.existsSync(htmlPath)) {
  console.error(
    "MISSING_PREVIEW: first run bash router/routercloud/webui/metro/build-preview.sh"
  );
  process.exit(1);
}

const rootHtml = fs.readFileSync(htmlPath, "utf8");
const dataTag = /(<template id="index-data">)([^<]+)(<\/template>)/;
const match = dataTag.exec(rootHtml);
if (!match || !rootHtml.includes("window.ROUTERCLOUD_PREVIEW = true")) {
  console.error("INVALID_PREVIEW: rebuild the Metro preview before starting");
  process.exit(1);
}

const rootData = JSON.parse(
  Buffer.from(match[2], "base64").toString("utf8")
);
if (rootData.kind !== "Index" || rootData.href !== "/") {
  console.error("INVALID_ROOT_SNAPSHOT");
  process.exit(1);
}

const folderData = {
  ...rootData,
  href: "/Testowy/",
  uri_prefix: "/",
  paths: [
    {
      name: "plik-testowy-z-podfolderu.txt",
      path_type: "File",
      mtime: 1791813600000,
      size: 1234,
    },
  ],
  dir_exists: true,
};

function page(data) {
  return rootHtml
    .replace(
      dataTag,
      (_all, open, _value, close) =>
        open +
        Buffer.from(JSON.stringify(data), "utf8").toString("base64") +
        close
    )
    // Absolute asset paths work equally at / and /Testowy/.
    .replace(
      /(href|src)="(index\.(?:css|js)|favicon\.ico)(\?[^"]*)?"/g,
      (_all, attr, filename, query = "") =>
        `${attr}="/${filename}${query}"`
    );
}

function reply(res, status, body, contentType) {
  res.writeHead(status, {
    "Content-Type": contentType,
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
  });
  res.end(body);
}

const mime = {
  "index.css": "text/css; charset=utf-8",
  "index.js": "text/javascript; charset=utf-8",
  "favicon.ico": "image/x-icon",
};
const server = http.createServer((req, res) => {
  if (req.method !== "GET") {
    return reply(res, 405, "Method not allowed", "text/plain");
  }

  const url = new URL(req.url, `http://${HOST}:${PORT}`);
  if (url.pathname === "/" || url.pathname === "/Testowy/") {
    const data = url.pathname === "/" ? rootData : folderData;
    if (url.searchParams.has("json")) {
      return reply(
        res, 200, JSON.stringify(data),
        "application/json; charset=utf-8"
      );
    }
    return reply(res, 200, page(data), "text/html; charset=utf-8");
  }

  const filename = url.pathname.slice(1);
  if (Object.hasOwn(mime, filename)) {
    const file = path.join(PREVIEW, filename);
    try {
      return reply(res, 200, fs.readFileSync(file), mime[filename]);
    } catch {
      return reply(res, 404, "File not found", "text/plain");
    }
  }

  return reply(res, 404, "Not found (isolated fixture)", "text/plain");
});

server.on("error", error => {
  console.error(`HOME_BROWSER_PREVIEW_ERROR=${error.message}`);
  process.exitCode = 1;
});

server.listen(PORT, HOST, () => {
  console.log("HOME_BROWSER_PREVIEW=READY");
  console.log(`ROOT=http://${HOST}:${PORT}/`);
  console.log(`SUBFOLDER=http://${HOST}:${PORT}/Testowy/`);
  console.log("PRODUCTION_CHANGED=NO");
});
