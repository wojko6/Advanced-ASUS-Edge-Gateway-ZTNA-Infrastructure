#!/usr/bin/env node
"use strict";

// Isolated unit test for the native image renderer. No network, no browser,
// no router, no production files. Run: node tests/test-routercloud-file-image-preview.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const repo = path.resolve(__dirname, "..");
const source = fs.readFileSync(
  path.join(repo, "router/routercloud/webui/metro/index.js"), "utf8"
);
const css = fs.readFileSync(
  path.join(repo, "router/routercloud/webui/metro/index.css"), "utf8"
);

const start = source.indexOf("const IMAGE_PREVIEW_FORMATS = [");
const stop = source.indexOf("const IFRAME_FORMATS = [", start);
const fnStart = source.indexOf("function setupRouterCloudImagePreview(");
const fnStop = source.indexOf("\nasync function setupEditorPage()", fnStart);

assert.ok(start !== -1 && stop > start, "native image allowlist must exist");
assert.ok(fnStart !== -1 && fnStop > fnStart, "image preview function must exist");

const setup = source.slice(fnStart, fnStop);
const allowlist = source.slice(start, stop);

assert.doesNotMatch(allowlist, /\.svg|\.pdf|\.html/i);
assert.doesNotMatch(setup, /\bfetch\s*\(|\.innerHTML|insertAdjacentHTML|URL\.createObjectURL/);
assert.match(setup, /image\.src\s*=\s*url/);
assert.match(setup, /image\.addEventListener\("error"/);
assert.match(setup, /fallback\.classList\.remove\("hidden"\)/);
assert.match(css, /body\.routercloud-file-view \.routercloud-image-preview img/);
assert.match(css, /object-fit:\s*contain/);
assert.match(css, /\.editor-page > \.routercloud-image-preview/);

const nodes = [];
const parent = {
  get last() { return nodes.at(-1); },
};

function fakeDocument() {
  return {
    querySelector(selector) {
      assert.equal(selector, ".editor-page");
      return parent;
    },
    createElement(tag) {
      return {
        tag,
        className: "",
        textContent: "",
        removed: false,
        events: {},
        classList: {
          removed: [],
          remove(name) { this.removed.push(name); },
        },
        appendChild(child) { this.child = child; },
        addEventListener(name, callback) { this.events[name] = callback; },
        insertAdjacentElement(position, element) {
          assert.equal(position, "afterend");
          nodes.push(element);
        },
        remove() { this.removed = true; },
      };
    },
  };
}

const script = allowlist + "\n" + setup + "\nsetupRouterCloudImagePreview;";
const ctx = {
  document: fakeDocument(),
  baseName(url) { return decodeURIComponent(url.split("/").at(-1)); },
};
const renderer = vm.runInNewContext(script, ctx);

function preview(extension) {
  nodes.length = 0;
  const fallback = ctx.document.createElement("div");
  const url = "http://127.0.0.1:8767/image" + extension;
  const result = renderer(url, extension, fallback);
  return { fallback, result, fig: parent.last, url };
}

for (const ext of [".ico", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]) {
  const { result, fig, url } = preview(ext);
  assert.equal(result, true);
  assert.equal(fig.tag, "figure");
  assert.equal(fig.className, "routercloud-image-preview");
  assert.equal(fig.child.tag, "img");
  assert.equal(fig.child.src, url);
  assert.equal(fig.child.loading, "eager");
  assert.match(fig.child.alt, /Podgląd obrazu:/);
}
for (const ext of [".pdf", ".svg", ".html", ".exe"]) {
  assert.equal(preview(ext).result, false);
  assert.equal(nodes.length, 0);
}

const { result, fig, fallback } = preview(".png");
assert.equal(result, true);
fig.child.events.error();
assert.equal(fig.removed, true);
assert.ok(fallback.classList.removed.includes("hidden"));
assert.match(fallback.textContent, /Nie udało się wyświetlić obrazu/);

assert.match(source, /if \(setupRouterCloudImagePreview\(url, ext, \$notEditable\)\) \{\s*return;/);
assert.match(source, /IFRAME_FORMATS\.find/);
console.log("ROUTERCLOUD_FILE_IMAGE_PREVIEW_TEST=PASS");
