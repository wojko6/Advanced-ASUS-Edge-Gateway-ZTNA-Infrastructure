#!/usr/bin/env node
"use strict";

// RouterCloud Home AJAX regression test. No external Node packages.
// Run: node tests/test-routercloud-home-ajax.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const app = process.env.ROUTERCLOUD_INDEX_JS ||
  path.join(__dirname, "../router/routercloud/webui/metro/index.js");
const source = fs.readFileSync(app, "utf8");
new vm.Script(source, { filename: "routercloud-metro-index.js" });

function harness(startPath = "/folder/") {
  const log = { fetches: [], notices: [], toasts: [], renders: 0, refreshes: 0, history: [], dashboardModes: [] };
  const location = {
    origin: "https://cloud.home.arpa",
    pathname: startPath,
    search: "",
    hash: "",
    href: "https://cloud.home.arpa" + startPath,
    reload() { log.reload = (log.reload || 0) + 1; },
  };
  const listeners = {};
  const search = { value: "test" };
  let respond = async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      kind: "Index", href: "/", uri_prefix: "/",
      paths: [{ name: "root.txt", path_type: "File", size: 1 }],
      dir_exists: true, storage: { total: 100, used: 20, available: 80 },
    }),
  });

  const sandbox = {
    URL, URLSearchParams, location,
    console: { warn() {} },
    setTimeout, clearTimeout,
    history: {
      pushState(state, _title, url) {
        log.history.push({ state, url });
        location.pathname = url;
        location.search = "";
        location.hash = "";
        location.href = location.origin + url;
      },
    },
    window: {
      location,
      addEventListener(event, handler) { listeners["window:" + event] = handler; },
    },
    document: {
      addEventListener(event, handler) { listeners["document:" + event] = handler; },
      getElementById(id) { return id === "search" ? search : null; },
      querySelector() { return { replaceChildren() {} }; },
    },
    async fetch(url) {
      log.fetches.push(new URL(String(url)));
      return respond(url);
    },
    testLog: log,
  };

  vm.createContext(sandbox);
  vm.runInContext(source, sandbox, { timeout: 3000 });
  sandbox.DATA = {
    kind: "Index", href: startPath, uri_prefix: "/",
    paths: [{ name: "old.txt", path_type: "File" }],
    dir_exists: true, storage: { total: 10, used: 2, available: 8 },
  };

  vm.runInContext(`
    addBreadcrumb = () => { testLog.renders++; };
    renderPathsTableHead = () => { testLog.renders++; };
    renderPathsTableBody = () => { testLog.renders++; };
    setupStorageInfo = () => { testLog.renders++; };
    refreshDashboardPanel = () => {
      testLog.renders++;
      testLog.dashboardModes.push(dashboardPanelMode);
    };
    updateArchiveSelectionUi = () => { testLog.renders++; };
    clearCompletedUploadRows = () => {};
    showRouterCloudToast = message => { testLog.toasts.push(message); };
    metroNotice = async options => { testLog.notices.push(options); };
    schedulePathRefresh = () => { testLog.refreshes++; };
    $pathsTableBody = { replaceChildren() {} };
    $pathsTable = { classList: { add() {} } };
    $emptyFolder = { classList: { add() {} } };
  `, sandbox);

  return {
    sandbox, log, location, listeners, search,
    setResponse(fn) { respond = fn; },
    navigate() { return vm.runInContext("navigateRouterCloudHome()", sandbox); },
    eval(code) { return vm.runInContext(code, sandbox); },
  };
}

async function main() {
  // Clicking Home when already at root is AJAX-only, with no navigation.
  {
    const h = harness("/");
    h.eval('dashboardPanelMode = "favorites"');
    await h.navigate();
    assert.equal(h.log.fetches.length, 0);
    assert.equal(h.log.refreshes, 1);
    assert.equal(h.log.history.length, 0);
    assert.equal(h.log.dashboardModes.at(-1), "recent");
    assert.equal(h.eval("dashboardPanelMode"), "recent");
  }

  // Static preview has no /?json endpoint. Home still resets the panel.
  {
    const h = harness("/");
    h.sandbox.window.ROUTERCLOUD_PREVIEW = true;
    h.eval('dashboardPanelMode = "favorites"');
    await h.navigate();
    assert.equal(h.log.fetches.length, 0);
    assert.equal(h.log.refreshes, 0);
    assert.equal(h.eval("dashboardPanelMode"), "recent");
    assert.equal(h.log.dashboardModes.at(-1), "recent");
  }

  // Switching from a subfolder commits root data after a successful JSON fetch.
  {
    const h = harness("/folder/");
    h.eval('dashboardPanelMode = "favorites"');
    await h.navigate();
    assert.equal(h.log.dashboardModes.at(-1), "recent");
    assert.equal(h.eval("dashboardPanelMode"), "recent");
    assert.equal(h.log.fetches.length, 1);
    assert.equal(h.log.fetches[0].pathname, "/");
    assert.equal(h.log.fetches[0].searchParams.has("json"), true);
    assert.equal(h.log.history.length, 1);
    assert.equal(h.location.pathname, "/");
    assert.equal(h.sandbox.DATA.href, "/");
    assert.equal(h.sandbox.DATA.paths[0].name, "root.txt");
    assert.equal(h.search.value, "");
    assert.equal(h.log.renders >= 6, true);
  }

  // An active upload must not be interrupted by a directory transition.
  {
    const h = harness("/folder/");
    h.eval("Uploader.runnings = 1");
    await h.navigate();
    assert.equal(h.log.fetches.length, 0);
    assert.equal(h.log.toasts.length, 1);
    assert.equal(h.location.pathname, "/folder/");
  }

  // A rejected response leaves URL and directory data unchanged.
  {
    const h = harness("/folder/");
    h.eval('dashboardPanelMode = "favorites"');
    h.setResponse(async () => { throw Error("offline"); });
    await h.navigate();
    assert.equal(h.eval("dashboardPanelMode"), "favorites");
    assert.equal(h.location.pathname, "/folder/");
    assert.equal(h.sandbox.DATA.paths[0].name, "old.txt");
    assert.equal(h.log.notices.length, 1);
  }

  // Old path-refresh responses must not overwrite root after navigation.
  {
    const h = harness("/folder/");
    let finishOldRequest;
    h.setResponse(async url => {
      if (new URL(String(url)).pathname === "/folder/") {
        return new Promise(resolve => { finishOldRequest = resolve; });
      }
      return {
        status: 200,
        json: async () => ({
          kind: "Index", href: "/", uri_prefix: "/",
          paths: [{ name: "root.txt", path_type: "File" }],
          dir_exists: true,
        }),
      };
    });
    const oldRefresh = h.eval("refreshCurrentIndex()");
    await h.navigate();
    finishOldRequest({
      status: 200,
      json: async () => ({ paths: [{ name: "stale.txt" }] }),
    });
    assert.equal(await oldRefresh, false);
    assert.equal(h.sandbox.DATA.paths[0].name, "root.txt");
  }

  // Modified clicks and file-editor routes retain native link handling.
  {
    const h = harness("/folder/");
    h.eval("setupRouterCloudHomeNavigation()");
    const handler = h.listeners["document:click"];
    function click(extra = {}) {
      return {
        button: 0, defaultPrevented: false,
        target: { closest: () => ({ origin: h.location.origin }) },
        preventDefault() { this.defaultPrevented = true; },
        ...extra,
      };
    }
    let event = click({ ctrlKey: true });
    handler(event);
    assert.equal(event.defaultPrevented, false);
    h.sandbox.DATA.kind = "Edit";
    event = click();
    handler(event);
    assert.equal(event.defaultPrevented, false);
    assert.equal(h.log.fetches.length, 0);
  }

  console.log("ROUTERCLOUD_HOME_AJAX_TEST=PASS");
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
