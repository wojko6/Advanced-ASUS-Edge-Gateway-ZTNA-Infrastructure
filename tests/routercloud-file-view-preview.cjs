#!/usr/bin/env node
"use strict";

// RouterCloud File View UX: isolated localhost fixture.
// Run after the stock Metro preview build; NO router/backend contact.
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

const HOST = "127.0.0.1";
const PORT = 8767;
const PREVIEW = "/tmp/routercloud-metro-preview";
const entry = path.join(PREVIEW, "index.html");
if (!fs.existsSync(entry)) {
  console.error("FILE_VIEW_FIXTURE_MISSING_PREVIEW: build Metro preview first");
  process.exit(1);
}

const template = fs.readFileSync(entry, "utf8");
const dataTag = /(<template id="index-data">)([^<]+)(<\/template>)/;
const match = dataTag.exec(template);
if (!match || !template.includes("window.ROUTERCLOUD_PREVIEW = true")) {
  console.error("FILE_VIEW_FIXTURE_INVALID_PREVIEW");
  process.exit(1);
}

const baseData = JSON.parse(Buffer.from(match[2], "base64").toString("utf8"));
if (baseData.kind !== "Index") {
  console.error("FILE_VIEW_FIXTURE_INVALID_ROOT");
  process.exit(1);
}

// Deterministic, locally generated 24x24 PNG fixture.
const samplePng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAIAAABvFaqvAAAAIklEQVR42mMUadjBQA3AxEAlMGrQqEGjBo0aNGrQqEHkAwCIgwF8iotDSwAAAABJRU5ErkJggg==",
  "base64"
);

const entries = {
  "/pixel.png": {
    kind: "View",
    editable: false,
    routercloud_allow_edit: false,
    bytes: samplePng,
    mime: "image/png",
  },
  "/broken.png": {
    kind: "View",
    editable: false,
    routercloud_allow_edit: false,
    bytes: Buffer.from("invalid image bytes", "utf8"),
    mime: "image/png",
  },
  "/demo.txt": {
    kind: "Edit",
    editable: true,
    routercloud_allow_edit: true,
    bytes: Buffer.from("RouterCloud File View UX — isolated text fixture\n", "utf8"),
    mime: "text/plain; charset=utf-8",
  },
  "/report.pdf": {
    kind: "View",
    editable: false,
    routercloud_allow_edit: false,
    bytes: Buffer.from("%PDF-1.4\n% Isolated fixture: PDF rendering not evaluated here\n", "utf8"),
    mime: "application/pdf",
  },
  "/favicon.ico": {
    kind: "View",
    editable: false,
    routercloud_allow_edit: false,
    bytes: fs.readFileSync(path.join(PREVIEW, "favicon.ico")),
    mime: "image/x-icon",
  },
};

function render(data) {
  return template.replace(
    dataTag,
    (_all, open, _encoded, close) => open +
      Buffer.from(JSON.stringify(data), "utf8").toString("base64") + close
  ).replace(
    /(href|src)="(index\.(?:css|js)|favicon\.ico)(\?[^"]*)?"/g,
    (_all, attr, file, query = "") => `${attr}="/${file}${query}"`
  );
}

function reply(res, status, body, mime) {
  res.writeHead(status, {
    "Content-Type": mime,
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
  });
  res.end(body);
}

const server = http.createServer((req, res) => {
  if (req.method !== "GET") {
    return reply(res, 405, "Method not allowed", "text/plain");
  }
  const url = new URL(req.url, `http://${HOST}:${PORT}`);
  if (url.pathname === "/") {
    return reply(res, 200, render(baseData), "text/html; charset=utf-8");
  }
  const entry = entries[url.pathname];
  if (entry && url.searchParams.has("view")) {
    const data = {
      href: url.pathname,
      kind: entry.kind,
      uri_prefix: "/",
      editable: entry.editable,
      routercloud_allow_edit: entry.routercloud_allow_edit,
      auth: false,
      user: null,
      allow_upload: false,
      allow_delete: false,
    };
    return reply(res, 200, render(data), "text/html; charset=utf-8");
  }
  if (entry) {
    return reply(res, 200, entry.bytes, entry.mime);
  }
  const asset = url.pathname.slice(1);
  const mimetypes = {
    "index.css": "text/css; charset=utf-8",
    "index.js": "text/javascript; charset=utf-8",
  };
  if (Object.hasOwn(mimetypes, asset)) {
    return reply(res, 200, fs.readFileSync(path.join(PREVIEW, asset)), mimetypes[asset]);
  }
  return reply(res, 404, "Not found", "text/plain");
});

server.on("error", err => {
  console.error(`FILE_VIEW_FIXTURE_ERROR=${err.message}`);
  process.exitCode = 1;
});
server.listen(PORT, HOST, () => {
  console.log("FILE_VIEW_FIXTURE=READY");
  console.log(`TEXT=http://${HOST}:${PORT}/demo.txt?view`);
  console.log(`PDF_LAYOUT=http://${HOST}:${PORT}/report.pdf?view`);
  console.log(`ICO_IMAGE=http://${HOST}:${PORT}/favicon.ico?view`);
  console.log(`PNG_IMAGE=http://${HOST}:${PORT}/pixel.png?view`);
  console.log(`IMAGE_ERROR_FALLBACK=http://${HOST}:${PORT}/broken.png?view`);
  console.log("PDF_BYTES=PLACEHOLDER_NOT_FOR_VIEWER_ACCEPTANCE");
  console.log("PRODUCTION_CHANGED=NO");
});
