#!/usr/bin/env node
"use strict";

// Static guard: file-only layout; no RouterCloud production or network access.
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const src = fs.readFileSync(
  path.join(root, "router/routercloud/webui/metro/index.js"), "utf8"
);
const css = fs.readFileSync(
  path.join(root, "router/routercloud/webui/metro/index.css"), "utf8"
);
const html = fs.readFileSync(
  path.join(root, "router/routercloud/webui/metro/index.html"), "utf8"
);
const assert = require("node:assert/strict");

assert.match(src, /function setupRouterCloudFileViewUx\(\)/);
assert.match(src, /DATA\.kind !== "Edit" && DATA\.kind !== "View"/);
assert.match(src, /document\.body\.classList\.add\("routercloud-file-view"\)/);
assert.match(src, /editorPage\.appendChild\(aside\)/);
assert.match(src, /editorPage\s*=\s*document\.querySelector\("\.editor-page"\)/);
assert.match(src, /setupRouterCloudFileViewUx\(\);/);
assert.match(src, /"ROUTERCLOUD_HOME_AJAX_V1"|ROUTERCLOUD_HOME_AJAX_V1/);
assert.match(src, /storage\.total - storage\.used - storage\.available/);

// CSS constraints: aside is part of the editor grid, never tall header row.
assert.match(css, /body\.routercloud-file-view \.head\s*\{[^}]*"actions \.";/);
assert.match(css, /body\.routercloud-file-view \.editor-page\s*\{[^}]*"preview info"/);
assert.match(css, /body\.routercloud-file-view \.editor-page > \.dashboard-aside\s*\{[^}]*grid-area: info/);
assert.match(css, /body\.routercloud-file-view \.editor-page > \.dashboard-aside\s*\{[^}]*align-self: start;/);
assert.match(css, /body\.routercloud-file-view \.editor-page > iframe\s*\{[^}]*grid-area: preview/);
assert.match(css, /@media \(max-width: 820px\)[\s\S]*body\.routercloud-file-view \.editor-page\s*\{[^}]*"preview"\s*"info"/);

// No source HTML relocation: moving the existing node for Edit/View only.
assert.match(html, /class="dashboard-aside"/);
assert.match(html, /class="editor-page hidden"/);
assert.match(html, /class="dashboard-storage"/);
assert.match(src, /contents\.replaceChildren\(\)/);
assert.match(src, /\.textContent = value/);
assert.doesNotMatch(src, /appendDetail\("Rozmiar"/);
assert.doesNotMatch(src, /appendDetail\("Modyfikacja"/);

console.log("ROUTERCLOUD_FILE_VIEW_LAYOUT_V2_TEST=PASS");
