/**
 * @typedef {object} PathItem
 * @property {"Dir"|"SymlinkDir"|"File"|"SymlinkFile"} path_type
 * @property {string} name
 * @property {number} mtime
 * @property {number} size
 */

/**
 * @typedef {object} StorageInfo
 * @property {number} total
 * @property {number} used
 * @property {number} available
 */

/**
 * @typedef {object} DATA
 * @property {string} href
 * @property {string} uri_prefix
 * @property {"Index" | "Edit" | "View"} kind
 * @property {PathItem[]} paths
 * @property {boolean} allow_upload
 * @property {boolean} allow_move
 * @property {boolean} allow_delete
 * @property {boolean} allow_search
 * @property {boolean} allow_archive
 * @property {boolean} auth
 * @property {string} user
 * @property {boolean} dir_exists
 * @property {StorageInfo} storage
 * @property {string} editable
 */

var DUFS_MAX_UPLOADINGS = 1;

/**
 * @type {DATA} DATA
 */
var DATA;

/**
 * @type {string}
 */
var DIR_EMPTY_NOTE;

/**
 * @type {PARAMS}
 * @typedef {object} PARAMS
 * @property {string} q
 * @property {string} sort
 * @property {string} order
 */
const PARAMS = Object.fromEntries(new URLSearchParams(window.location.search).entries());

const IFRAME_FORMATS = [
  ".pdf",
  ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
  ".mp4", ".mov", ".avi", ".wmv", ".flv", ".webm",
  ".mp3", ".ogg", ".wav", ".m4a",
];

const MAX_SUBPATHS_COUNT = 1000;

const ICONS = {
  dir: `<svg height="16" viewBox="0 0 14 16" width="14"><path fill-rule="evenodd" d="M13 4H7V3c0-.66-.31-1-1-1H1c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1V5c0-.55-.45-1-1-1zM6 4H1V3h5v1z"></path></svg>`,
  symlinkFile: `<svg height="16" viewBox="0 0 12 16" width="12"><path fill-rule="evenodd" d="M8.5 1H1c-.55 0-1 .45-1 1v12c0 .55.45 1 1 1h10c.55 0 1-.45 1-1V4.5L8.5 1zM11 14H1V2h7l3 3v9zM6 4.5l4 3-4 3v-2c-.98-.02-1.84.22-2.55.7-.71.48-1.19 1.25-1.45 2.3.02-1.64.39-2.88 1.13-3.73.73-.84 1.69-1.27 2.88-1.27v-2H6z"></path></svg>`,
  symlinkDir: `<svg height="16" viewBox="0 0 14 16" width="14"><path fill-rule="evenodd" d="M13 4H7V3c0-.66-.31-1-1-1H1c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1V5c0-.55-.45-1-1-1zM1 3h5v1H1V3zm6 9v-2c-.98-.02-1.84.22-2.55.7-.71.48-1.19 1.25-1.45 2.3.02-1.64.39-2.88 1.13-3.73C4.86 8.43 5.82 8 7.01 8V6l4 3-4 3H7z"></path></svg>`,
  file: `<svg height="16" viewBox="0 0 12 16" width="12"><path fill-rule="evenodd" d="M6 5H2V4h4v1zM2 8h7V7H2v1zm0 2h7V9H2v1zm0 2h7v-1H2v1zm10-7.5V14c0 .55-.45 1-1 1H1c-.55 0-1-.45-1-1V2c0-.55.45-1 1-1h7.5L12 4.5zM11 5L8 2H1v12h10V5z"></path></svg>`,
  download: `<svg width="16" height="16" viewBox="0 0 16 16"><path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/><path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z"/></svg>`,
  move: `<svg width="16" height="16" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M1.5 1.5A.5.5 0 0 0 1 2v4.8a2.5 2.5 0 0 0 2.5 2.5h9.793l-3.347 3.346a.5.5 0 0 0 .708.708l4.2-4.2a.5.5 0 0 0 0-.708l-4-4a.5.5 0 0 0-.708.708L13.293 8.3H3.5A1.5 1.5 0 0 1 2 6.8V2a.5.5 0 0 0-.5-.5z"/></svg>`,
  edit: `<svg width="16" height="16" viewBox="0 0 16 16"><path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293l6.5-6.5zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325z"/></svg>`,
  delete: `<svg width="16" height="16" viewBox="0 0 16 16"><path d="M6.854 7.146a.5.5 0 1 0-.708.708L7.293 9l-1.147 1.146a.5.5 0 0 0 .708.708L8 9.707l1.146 1.147a.5.5 0 0 0 .708-.708L8.707 9l1.147-1.146a.5.5 0 0 0-.708-.708L8 8.293 6.854 7.146z"/><path d="M14 14V4.5L9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2zM9.5 3A1.5 1.5 0 0 0 11 4.5h2V14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h5.5v2z"/></svg>`,
  view: `<svg width="16" height="16" viewBox="0 0 16 16"><path d="M4 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2zm0 1h8a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1"/></svg>`,
}

/**
 * @type Map<string, Uploader>
 */
const failUploaders = new Map();

/**
 * @type Element
 */
let $pathsTable;
/**
 * @type Element
 */
let $pathsTableHead;
/**
 * @type Element
 */
let $pathsTableBody;
/**
 * @type Element
 */
let $uploadersTable;
/**
 * @type Element
 */
let $emptyFolder;
/**
 * @type Element
 */
let $storageInfo;
/**
 * @type Element
 */
let $editor;
/**
 * @type Element
 */
let $loginBtn;
/**
 * @type Element
 */
let $logoutBtn;
/**
 * @type Element
 */
let $userName;

/**
 * RouterCloud Metro dialog system
 */

function metroDialog({
  title,
  message = "",
  mode = "notice",
  label = "",
  value = "",
  primaryText = "OK",
  cancelText = "Anuluj",
  danger = false,
  validate = null,
}) {
  return new Promise(resolve => {
    const dialog = document.getElementById("metro-dialog");
    const $title = document.getElementById("metro-dialog-title");
    const $message = document.getElementById("metro-dialog-message");
    const $field = document.getElementById("metro-dialog-field");
    const $label = document.getElementById("metro-dialog-label");
    const $input = document.getElementById("metro-dialog-input");
    const $error = document.getElementById("metro-dialog-error");
    const $cancel = document.getElementById("metro-dialog-cancel");
    const $primary = document.getElementById("metro-dialog-primary");
    const $close = dialog.querySelector(".metro-dialog-close");

    if (!dialog) {
      resolve(mode === "confirm" ? false : mode === "prompt" ? null : undefined);
      return;
    }

    $title.textContent = title;
    $message.textContent = message;
    $message.classList.toggle("hidden", !message);

    const needsInput = mode === "prompt";
    $field.classList.toggle("hidden", !needsInput);
    $label.textContent = label;
    $input.textContent = value;
    $input.dataset.placeholder = label;

    $error.textContent = "";
    $error.classList.add("hidden");

    $primary.textContent = primaryText;
    $primary.classList.toggle("metro-dialog-button-danger", danger);

    const showCancel = mode !== "notice";
    $cancel.classList.toggle("hidden", !showCancel);
    $cancel.textContent = cancelText;

    document.body.classList.add("metro-dialog-open");

    let settled = false;

    const cleanup = result => {
      if (settled) return;
      settled = true;

      document.body.classList.remove("metro-dialog-open");

      $primary.classList.remove("metro-dialog-button-danger");

      dialog.removeEventListener("cancel", onCancel);
      dialog.removeEventListener("close", onClose);
      $cancel.removeEventListener("click", cancel);
      $close.removeEventListener("click", cancel);
      $primary.removeEventListener("click", submit);
      $input.removeEventListener("keydown", onInputKeyDown);
      $input.removeEventListener("input", onInputChange);

      if (dialog.open) {
        dialog.close();
      }

      resolve(result);
    };

    const cancel = () => {
      if (mode === "confirm") {
        cleanup(false);
      } else if (mode === "prompt") {
        cleanup(null);
      } else {
        cleanup(undefined);
      }
    };

    const onCancel = event => {
      event.preventDefault();
      cancel();
    };

    const onClose = () => {
      if (!settled) cancel();
    };

    const submit = event => {
      event.preventDefault();

      if (mode === "prompt") {
        const result = ($input.textContent || "").trim();

        if (validate) {
          const validationError = validate(result);

          if (validationError) {
            $error.textContent = validationError;
            $error.classList.remove("hidden");
            $input.focus();
            return;
          }
        }

        cleanup(result);
        return;
      }

      if (mode === "confirm") {
        cleanup(true);
        return;
      }

      cleanup(undefined);
    };

    const onInputKeyDown = event => {
      if (event.key === "Enter") {
        event.preventDefault();
        submit(event);
      }
    };

    const onInputChange = () => {
      const text = $input.textContent || "";

      if (text.length > 255) {
        $input.textContent = text.slice(0, 255);

        const selection = window.getSelection();
        const range = document.createRange();

        range.selectNodeContents($input);
        range.collapse(false);

        selection.removeAllRanges();
        selection.addRange(range);
      }
    };

    $input.addEventListener("keydown", onInputKeyDown);
    $input.addEventListener("input", onInputChange);

    dialog.addEventListener("cancel", onCancel);
    dialog.addEventListener("close", onClose);
    $cancel.addEventListener("click", cancel);
    $close.addEventListener("click", cancel);
    $primary.addEventListener("click", submit);

    dialog.showModal();

    requestAnimationFrame(() => {
      if (needsInput) {
        $input.focus();

        const selection = window.getSelection();
        const range = document.createRange();

        range.selectNodeContents($input);
        selection.removeAllRanges();
        selection.addRange(range);
      } else {
        $primary.focus();
      }
    });
  });
}

function metroPrompt({
  title,
  message = "",
  label = "Nazwa",
  value = "",
  primaryText = "Zapisz",
  validate = null,
}) {
  return metroDialog({
    title,
    message,
    mode: "prompt",
    label,
    value,
    primaryText,
    validate,
  });
}

function metroConfirm({
  title,
  message,
  primaryText = "Potwierdź",
  danger = false,
}) {
  return metroDialog({
    title,
    message,
    mode: "confirm",
    primaryText,
    danger,
  });
}

function metroNotice({
  title,
  message,
  primaryText = "OK",
}) {
  return metroDialog({
    title,
    message,
    mode: "notice",
    primaryText,
  });
}

function validateNewName(name) {
  if (!name) {
    return "Nazwa nie może być pusta.";
  }

  if (
    name === "." ||
    name === ".." ||
    name.includes("/") ||
    name.includes("\\")
  ) {
    return "Podaj wyłącznie nazwę pliku lub folderu, bez ścieżki.";
  }

  return "";
}

// manage unload event to prevent leaving with uploads in progress
const beforeUnloadHandler = (event) => {
  if (Uploader.queues.length > 0 || Uploader.runnings > 0) {
    event.preventDefault();
    event.returnValue = '';
    return ''; // for some browsers
  }
};

// Produce table when window loads
window.addEventListener("DOMContentLoaded", async () => {
  const $indexData = document.getElementById('index-data');
  if (!$indexData) {
    await metroNotice({
      title: "Brak danych",
      message: "RouterCloud nie otrzymał danych potrzebnych do wyświetlenia widoku.",
    });
    return;
  }

  DATA = JSON.parse(decodeBase64($indexData.innerHTML));
  DIR_EMPTY_NOTE = PARAMS.q ? 'Brak wyników' : DATA.dir_exists ? 'Pusty folder' : 'Folder zostanie utworzony po przesłaniu pliku';

  await ready();
});

async function ready() {
  $pathsTable = document.querySelector(".paths-table");
  $pathsTableHead = document.querySelector(".paths-table thead");
  $pathsTableBody = document.querySelector(".paths-table tbody");
  $uploadersTable = document.querySelector(".uploaders-table");
  $emptyFolder = document.querySelector(".empty-folder");
  $storageInfo = document.querySelector(".storage-info");
  $editor = document.querySelector(".editor");
  $loginBtn = document.querySelector(".login-btn");
  $logoutBtn = document.querySelector(".logout-btn");
  $userName = document.querySelector(".user-name");

  window.addEventListener('beforeunload', beforeUnloadHandler);

  addBreadcrumb(DATA.href, DATA.uri_prefix);

  if (DATA.kind === "Index") {
    document.title = `RouterCloud — ${DATA.href}`;
    document.querySelector(".index-page").classList.remove("hidden");

    await setupIndexPage();
  } else if (DATA.kind === "Edit") {
    document.title = `Edycja ${DATA.href} — RouterCloud`;
    document.querySelector(".editor-page").classList.remove("hidden");

    await setupEditorPage();
  } else if (DATA.kind === "View") {
    document.title = `Podgląd ${DATA.href} — RouterCloud`;
    document.querySelector(".editor-page").classList.remove("hidden");

    await setupEditorPage();
  }
}

class Uploader {
  /**
   *
   * @param {File} file
   * @param {string[]} pathParts
   */
  constructor(file, pathParts) {
    /**
     * @type Element
     */
    this.$uploadStatus = null
    this.uploaded = 0;
    this.uploadOffset = 0;
    this.lastUptime = 0;
    this.name = [...pathParts, file.name].join("/");
    this.idx = Uploader.globalIdx++;
    this.file = file;
    this.url = newUrl(this.name);
  }

  upload() {
    const { idx, name, url } = this;
    const encodedName = encodedStr(name);
    $uploadersTable.insertAdjacentHTML("beforeend", `
  <tr id="upload${idx}" class="uploader">
    <td class="path cell-icon">
      ${getPathSvg()}
    </td>
    <td class="path cell-name">
      <a href="${url}">${encodedName}</a>
    </td>
    <td class="cell-status upload-status" id="uploadStatus${idx}"></td>
  </tr>`);
    $uploadersTable.classList.remove("hidden");
    $emptyFolder.classList.add("hidden");
    this.$uploadStatus = document.getElementById(`uploadStatus${idx}`);
    this.$uploadStatus.innerHTML = '-';
    this.$uploadStatus.addEventListener("click", e => {
      const nodeId = e.target.id;
      const matches = /^retry(\d+)$/.exec(nodeId);
      if (matches) {
        const id = parseInt(matches[1]);
        let uploader = failUploaders.get(id);
        if (uploader) uploader.retry();
      }
    });
    Uploader.queues.push(this);
    Uploader.runQueue();
  }

  ajax() {
    const { url } = this;

    this.uploaded = 0;
    this.lastUptime = Date.now();

    const ajax = new XMLHttpRequest();
    ajax.upload.addEventListener("progress", e => this.progress(e), false);
    ajax.addEventListener("readystatechange", () => {
      if (ajax.readyState === 4) {
        if (ajax.status >= 200 && ajax.status < 300) {
          this.complete();
        } else {
          if (ajax.status != 0) {
            this.fail(`${ajax.status} ${ajax.statusText}`);
          }
        }
      }
    })
    ajax.addEventListener("error", () => this.fail(), false);
    ajax.addEventListener("abort", () => this.fail(), false);
    if (this.uploadOffset > 0) {
      ajax.open("PATCH", url);
      ajax.setRequestHeader("X-Update-Range", "append");
      ajax.send(this.file.slice(this.uploadOffset));
    } else {
      ajax.open("PUT", url);
      ajax.send(this.file);
      // setTimeout(() => ajax.abort(), 3000);
    }
  }

  async retry() {
    const { url } = this;
    let res = await fetch(url, {
      method: "HEAD",
    });
    let uploadOffset = 0;
    if (res.status == 200) {
      let value = res.headers.get("content-length");
      uploadOffset = parseInt(value) || 0;
    }
    this.uploadOffset = uploadOffset;
    this.ajax();
  }

  progress(event) {
    const now = Date.now();
    const elapsed = now - this.lastUptime;
    if (elapsed < 300) return; // throttle update for safari
    const speed = (event.loaded - this.uploaded) / elapsed * 1000;
    const [speedValue, speedUnit] = formatFileSize(speed);
    const speedText = `${speedValue} ${speedUnit}/s`;
    const progress = formatPercent(((event.loaded + this.uploadOffset) / this.file.size) * 100);
    const duration = formatDuration((event.total - event.loaded) / speed);
    this.$uploadStatus.innerHTML = `<span style="width: 80px;">${speedText}</span><span style="margin-left: 5px;">${progress} ${duration}</span>`;
    this.uploaded = event.loaded;
    this.lastUptime = now;
  }

  complete() {
    const $uploadStatusNew = this.$uploadStatus.cloneNode(true);
    $uploadStatusNew.innerHTML = `✓`;
    this.$uploadStatus.parentNode.replaceChild($uploadStatusNew, this.$uploadStatus);
    this.$uploadStatus = null;
    failUploaders.delete(this.idx);
    Uploader.runnings--;
    Uploader.runQueue();
  }

  fail(reason = "") {
    this.$uploadStatus.innerHTML = `<span style="width: 20px;" title="${reason}">✗</span><span class="retry-btn" id="retry${this.idx}" title="Ponów">↻</span>`;
    failUploaders.set(this.idx, this);
    Uploader.runnings--;
    Uploader.runQueue();
  }
}

Uploader.globalIdx = 0;

Uploader.runnings = 0;

Uploader.auth = false;

/**
 * @type Uploader[]
 */
Uploader.queues = [];


Uploader.runQueue = async () => {
  if (Uploader.runnings >= DUFS_MAX_UPLOADINGS) return;
  if (Uploader.queues.length == 0) return;
  Uploader.runnings++;
  let uploader = Uploader.queues.shift();
  if (!Uploader.auth) {
    Uploader.auth = true;
    try {
      await checkAuth();
    } catch {
      Uploader.auth = false;
    }
  }
  uploader.ajax();
}

/**
 * Add breadcrumb
 * @param {string} href
 * @param {string} uri_prefix
 */
function addBreadcrumb(href, uri_prefix) {
  const $breadcrumb = document.querySelector(".breadcrumb");
  let parts = [];
  if (href === "/") {
    parts = [""];
  } else {
    parts = href.split("/");
  }
  const len = parts.length;
  let path = uri_prefix;
  for (let i = 0; i < len; i++) {
    const name = parts[i];
    if (i > 0) {
      if (!path.endsWith("/")) {
        path += "/";
      }
      path += encodeURIComponent(name);
    }
    const encodedName = encodedStr(name);
    if (i === 0) {
      $breadcrumb.insertAdjacentHTML("beforeend", `<a href="${path}" title="Katalog główny"><svg width="16" height="16" viewBox="0 0 16 16"><path d="M6.5 14.5v-3.505c0-.245.25-.495.5-.495h2c.25 0 .5.25.5.5v3.5a.5.5 0 0 0 .5.5h4a.5.5 0 0 0 .5-.5v-7a.5.5 0 0 0-.146-.354L13 5.793V2.5a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v1.293L8.354 1.146a.5.5 0 0 0-.708 0l-6 6A.5.5 0 0 0 1.5 7.5v7a.5.5 0 0 0 .5.5h4a.5.5 0 0 0 .5-.5z"/></svg></a>`);
    } else if (i === len - 1) {
      $breadcrumb.insertAdjacentHTML("beforeend", `<b>${encodedName}</b>`);
    } else {
      $breadcrumb.insertAdjacentHTML("beforeend", `<a href="${path}">${encodedName}</a>`);
    }
    if (i !== len - 1) {
      $breadcrumb.insertAdjacentHTML("beforeend", `<span class="separator">/</span>`);
    }
  }
}

function formatStorageBytes(size) {
  const [value, unit] = formatFileSize(size);
  const localizedValue = String(value).replace(".", ",");
  return `${localizedValue} ${unit}`;
}

function setupStorageInfo() {
  const storage = DATA.storage;

  if (!storage || !storage.total || !$storageInfo) {
    return;
  }

  const usedPercent = (storage.used / storage.total) * 100;
  const percent = formatPercent(usedPercent).replace(".", ",");

  $storageInfo.textContent =
    `Dysk: ${formatStorageBytes(storage.used)} zajęte • ` +
    `${formatStorageBytes(storage.available)} dostępne • ` +
    `${formatStorageBytes(storage.total)} razem • ${percent}`;

  $storageInfo.classList.remove("hidden");
}

async function setupIndexPage() {
  setupStorageInfo();

  if (DATA.allow_archive) {
    const $download = document.querySelector(".download");
    $download.href = baseUrl() + "?zip";
    $download.title = "Pobierz jako .zip";
    $download.classList.add("dlwt");
    $download.classList.remove("hidden");
  }

  if (DATA.allow_upload) {
    setupDropzone();
    setupUploadFile();
    setupNewFolder();
    setupNewFile();
  }

  if (DATA.auth) {
    await setupAuth();
  }

  if (DATA.allow_search) {
    setupSearch();
  }

  renderPathsTableHead();
  renderPathsTableBody();

  if (DATA.user) {
    setupDownloadWithToken();
  }
}

/**
 * Render path table thead
 */
function renderPathsTableHead() {
  const headerItems = [
    {
      name: "name",
      props: `colspan="2"`,
      text: "Nazwa",
    },
    {
      name: "mtime",
      props: ``,
      text: "Ostatnia modyfikacja",
    },
    {
      name: "size",
      props: ``,
      text: "Rozmiar",
    }
  ];
  $pathsTableHead.insertAdjacentHTML("beforeend", `
    <tr>
      ${headerItems.map(item => {
    let svg = `<svg width="12" height="12" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M11.5 15a.5.5 0 0 0 .5-.5V2.707l3.146 3.147a.5.5 0 0 0 .708-.708l-4-4a.5.5 0 0 0-.708 0l-4 4a.5.5 0 1 0 .708.708L11 2.707V14.5a.5.5 0 0 0 .5.5zm-7-14a.5.5 0 0 1 .5.5v11.793l3.146-3.147a.5.5 0 0 1 .708.708l-4 4a.5.5 0 0 1-.708 0l-4-4a.5.5 0 0 1 .708-.708L4 13.293V1.5a.5.5 0 0 1 .5-.5z"/></svg>`;
    let order = "desc";
    if (PARAMS.sort === item.name) {
      if (PARAMS.order === "desc") {
        order = "asc";
        svg = `<svg width="12" height="12" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M8 1a.5.5 0 0 1 .5.5v11.793l3.146-3.147a.5.5 0 0 1 .708.708l-4 4a.5.5 0 0 1-.708 0l-4-4a.5.5 0 0 1 .708-.708L7.5 13.293V1.5A.5.5 0 0 1 8 1z"/></svg>`
      } else {
        svg = `<svg width="12" height="12" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M8 15a.5.5 0 0 0 .5-.5V2.707l3.146 3.147a.5.5 0 0 0 .708-.708l-4-4a.5.5 0 0 0-.708 0l-4 4a.5.5 0 1 0 .708.708L7.5 2.707V14.5a.5.5 0 0 0 .5.5z"/></svg>`
      }
    }
    const qs = new URLSearchParams({ ...PARAMS, order, sort: item.name }).toString();
    const icon = `<span>${svg}</span>`
    return `<th class="cell-${item.name}" ${item.props}><a href="?${qs}">${item.text}${icon}</a></th>`
  }).join("\n")}
      <th class="cell-actions">Akcje</th>
    </tr>
  `);
}

/**
 * Render path table tbody
 */
function renderPathsTableBody() {
  if (DATA.paths && DATA.paths.length > 0) {
    const len = DATA.paths.length;
    if (len > 0) {
      $pathsTable.classList.remove("hidden");
    }
    for (let i = 0; i < len; i++) {
      addPath(DATA.paths[i], i);
    }
  } else {
    $emptyFolder.textContent = DIR_EMPTY_NOTE;
    $emptyFolder.classList.remove("hidden");
  }
}

/**
 * Add pathitem
 * @param {PathItem} file
 * @param {number} index
 */
function addPath(file, index) {
  const encodedName = encodedStr(file.name);
  let url = newUrl(file.name);
  let actionDelete = "";
  let actionDownload = "";
  let actionMove = "";
  let actionEdit = "";
  let actionView = "";
  let isDir = file.path_type.endsWith("Dir");
  if (isDir) {
    url += "/";
    if (DATA.allow_archive) {
      actionDownload = `
      <div class="action-btn">
        <a class="dlwt" href="${url}?zip" title="Pobierz folder jako plik .zip" download>${ICONS.download}</a>
      </div>`;
    }
  } else {
    actionDownload = `
    <div class="action-btn" >
      <a class="dlwt" href="${url}" title="Pobierz plik" download>${ICONS.download}</a>
    </div>`;
  }
  if (DATA.allow_move) {
    actionMove = `<div onclick="movePath(${index})" class="action-btn" id="moveBtn${index}" title="Zmień nazwę">${ICONS.move}</div>`;
  }
  if (DATA.allow_delete) {
    if (DATA.allow_upload && !isDir) {
      actionEdit = `<a class="action-btn" title="Edytuj plik" target="_blank" href="${url}?edit">${ICONS.edit}</a>`;
    }
    actionDelete = `
    <div onclick="deletePath(${index})" class="action-btn" id="deleteBtn${index}" title="Usuń">${ICONS.delete}</div>`;
  }
  if (!actionEdit && !isDir) {
    actionView = `<a class="action-btn" title="Wyświetl plik" target="_blank" href="${url}?view">${ICONS.view}</a>`;
  }
  let actionCell = `
  <td class="cell-actions">
    ${actionDownload}
    ${actionView}
    ${actionMove}
    ${actionDelete}
    ${actionEdit}
  </td>`;

  let sizeDisplay = isDir ? formatDirSize(file.size) : formatFileSize(file.size).join(" ");

  $pathsTableBody.insertAdjacentHTML("beforeend", `
<tr id="addPath${index}">
  <td class="path cell-icon">
    ${getPathSvg(file.path_type)}
  </td>
  <td class="path cell-name">
    <a href="${url}" ${isDir ? "" : `target="_blank"`}>${encodedName}</a>
  </td>
  <td class="cell-mtime">${formatMtime(file.mtime)}</td>
  <td class="cell-size">${sizeDisplay}</td>
  ${actionCell}
</tr>`);
}

function setupDropzone() {
  ["drag", "dragstart", "dragend", "dragover", "dragenter", "dragleave", "drop"].forEach(name => {
    document.addEventListener(name, e => {
      e.preventDefault();
      e.stopPropagation();
    });
  });
  document.addEventListener("drop", async e => {
    if (!e.dataTransfer.items[0].webkitGetAsEntry) {
      const files = Array.from(e.dataTransfer.files).filter(v => v.size > 0);
      for (const file of files) {
        new Uploader(file, []).upload();
      }
    } else {
      const entries = [];
      const len = e.dataTransfer.items.length;
      for (let i = 0; i < len; i++) {
        entries.push(e.dataTransfer.items[i].webkitGetAsEntry());
      }
      addFileEntries(entries, []);
    }
  });
}

async function setupAuth() {
  if (DATA.user) {
    $logoutBtn.classList.remove("hidden");
    $logoutBtn.addEventListener("click", logout);
    $userName.textContent = DATA.user;
  } else {
    $loginBtn.classList.remove("hidden");
    $loginBtn.addEventListener("click", () => {
      location.href = "/__routercloud/login";
    });
  }
}

function setupDownloadWithToken() {
  document.querySelectorAll("a.dlwt").forEach(link => {
    link.addEventListener("click", async e => {
      e.preventDefault();
      try {
        const link = e.currentTarget || e.target;
        const originalHref = link.getAttribute("href");
        const tokengenUrl = new URL(originalHref);
        tokengenUrl.searchParams.set("tokengen", "");
        const res = await fetch(tokengenUrl);
        if (!res.ok) throw new Error("Nie udało się pobrać tokenu");
        const token = await res.text();
        const downloadUrl = new URL(originalHref);
        downloadUrl.searchParams.set("token", token);
        const tempA = document.createElement("a");
        tempA.href = downloadUrl.toString();
        tempA.download = "";
        document.body.appendChild(tempA);
        tempA.click();
        document.body.removeChild(tempA);
      } catch (err) {
        await metroNotice({
          title: "Nie udało się pobrać pliku",
          message: err.message,
        });
      }
    });
  });
}

function setupSearch() {
  const $searchbar = document.querySelector(".searchbar");
  $searchbar.classList.remove("hidden");
  $searchbar.addEventListener("submit", event => {
    event.preventDefault();
    const formData = new FormData($searchbar);
    const q = formData.get("q");
    let href = baseUrl();
    if (q) {
      href += "?q=" + q;
    }
    location.href = href;
  });
  if (PARAMS.q) {
    document.getElementById('search').value = PARAMS.q;
  }
}

function setupUploadFile() {
  document.querySelector(".upload-file").classList.remove("hidden");
  document.getElementById("file").addEventListener("change", async e => {
    const files = e.target.files;
    for (let file of files) {
      new Uploader(file, []).upload();
    }
  });
}

function setupNewFolder() {
  const $newFolder = document.querySelector(".new-folder");
  $newFolder.classList.remove("hidden");
  $newFolder.addEventListener("click", async () => {
    const name = await metroPrompt({
      title: "Nowy folder",
      message: "Utwórz nowy folder w bieżącej lokalizacji.",
      label: "Nazwa folderu",
      primaryText: "Utwórz",
      validate: validateNewName,
    });

    if (name) {
      await createFolder(name);
    }
  });
}

function setupNewFile() {
  const $newFile = document.querySelector(".new-file");
  $newFile.classList.remove("hidden");
  $newFile.addEventListener("click", async () => {
    const name = await metroPrompt({
      title: "Nowy plik",
      message: "Utwórz nowy plik w bieżącej lokalizacji.",
      label: "Nazwa pliku",
      primaryText: "Utwórz",
      validate: validateNewName,
    });

    if (name) {
      await createFile(name);
    }
  });
}

async function setupEditorPage() {
  const url = baseUrl();

  const $download = document.querySelector(".download");
  $download.classList.remove("hidden");
  $download.href = url;

  if (DATA.kind == "Edit") {
    if (DATA.allow_move) {
      const $moveFile = document.querySelector(".move-file");
      $moveFile.classList.remove("hidden");
      $moveFile.addEventListener("click", async () => {
        const query = location.href.slice(url.length);
        const newFileUrl = await doMovePath(url);
        if (newFileUrl) {
          location.href = newFileUrl + query;
        }
      });
    }

    if (DATA.allow_delete) {
      const $deleteFile = document.querySelector(".delete-file");
      $deleteFile.classList.remove("hidden");
      $deleteFile.addEventListener("click", async () => {
        const url = baseUrl();
        const name = baseName(url);
        await doDeletePath(name, url, () => {
          location.href = location.href.split("/").slice(0, -1).join("/");
        });
      });
    }

    if (DATA.editable) {
      const $saveBtn = document.querySelector(".save-btn");
      $saveBtn.classList.remove("hidden");
      $saveBtn.addEventListener("click", saveChange);
    }
  } else if (DATA.kind == "View") {
    $editor.readonly = true;
  }

  if (!DATA.editable) {
    const $notEditable = document.querySelector(".not-editable");
    const url = baseUrl();
    const ext = extName(baseName(url));
    if (IFRAME_FORMATS.find(v => v === ext)) {
      $notEditable.insertAdjacentHTML("afterend", `<iframe src="${url}" sandbox width="100%" height="${window.innerHeight - 100}px"></iframe>`);
    } else {
      $notEditable.classList.remove("hidden");
      $notEditable.textContent = "Nie można edytować: plik jest zbyt duży lub binarny.";
    }
    return;
  }

  $editor.classList.remove("hidden");
  try {
    const res = await fetch(baseUrl());
    await assertResOK(res);
    const encoding = getEncoding(res.headers.get("content-type"));
    if (encoding === "utf-8") {
      $editor.value = await res.text();
    } else {
      const bytes = await res.arrayBuffer();
      const dataView = new DataView(bytes);
      const decoder = new TextDecoder(encoding);
      $editor.value = decoder.decode(dataView);
    }
  } catch (err) {
    await metroNotice({
      title: "Nie udało się pobrać pliku",
      message: err.message,
    });
  }
}

/**
 * Delete path
 * @param {number} index
 * @returns
 */
async function deletePath(index) {
  const file = DATA.paths[index];
  if (!file) return;
  await doDeletePath(file.name, newUrl(file.name), () => {
    document.getElementById(`addPath${index}`)?.remove();
    DATA.paths[index] = null;
    if (!DATA.paths.find(v => !!v)) {
      $pathsTable.classList.add("hidden");
      $emptyFolder.textContent = DIR_EMPTY_NOTE;
      $emptyFolder.classList.remove("hidden");
    }
  });
}

async function doDeletePath(name, url, cb) {
  const confirmed = await metroConfirm({
    title: "Usunąć element?",
    message: `Element „${name}” zostanie trwale usunięty.`,
    primaryText: "Usuń",
    danger: true,
  });

  if (!confirmed) return;
  try {
    await checkAuth();
    const res = await fetch(url, {
      method: "DELETE",
    });
    await assertResOK(res);
    cb();
  } catch (err) {
    await metroNotice({
      title: "Nie można usunąć",
      message: `Element „${name}” nie został usunięty.\n\n${err.message}`,
    });
  }
}

/**
 * Move path
 * @param {number} index
 * @returns
 */
async function movePath(index) {
  const file = DATA.paths[index];
  if (!file) return;
  const fileUrl = newUrl(file.name);
  const newFileUrl = await doMovePath(fileUrl);
  if (newFileUrl) {
    location.href = newFileUrl.split("/").slice(0, -1).join("/");
  }
}

async function doMovePath(fileUrl) {
  const fileUrlObj = new URL(fileUrl);
  const prefix = DATA.uri_prefix.slice(0, -1);
  const filePath = decodeURIComponent(fileUrlObj.pathname.slice(prefix.length));

  const lastSlash = filePath.lastIndexOf("/");
  const parentPath = filePath.slice(0, lastSlash + 1);
  const currentName = filePath.slice(lastSlash + 1);

  const newName = await metroPrompt({
    title: "Zmień nazwę",
    message: `Zmieniasz nazwę elementu „${currentName}”.`,
    label: "Nowa nazwa",
    value: currentName,
    primaryText: "Zmień nazwę",
    validate: validateNewName,
  });

  if (!newName || newName === currentName) return;

  const newPath = parentPath + newName;
  const newFileUrl =
    fileUrlObj.origin +
    prefix +
    newPath.split("/").map(encodeURIComponent).join("/");

  try {
    await checkAuth();

    const res = await fetch(fileUrl, {
      method: "MOVE",
      headers: {
        "Destination": newFileUrl,
      }
    });

    if (res.status === 409) {
      await metroNotice({
        title: "Nazwa jest już zajęta",
        message: `W tym folderze istnieje już element o nazwie „${newName}”.`,
      });
      return;
    }

    await assertResOK(res);
    return newFileUrl;
  } catch (err) {
    await metroNotice({
      title: "Nie udało się zmienić nazwy",
      message: `Nie można zmienić nazwy „${currentName}” na „${newName}”.\n\n${err.message}`,
    });
  }
}


/**
 * Save editor change
 */
async function saveChange() {
  try {
    await fetch(baseUrl(), {
      method: "PUT",
      body: $editor.value,
    });
    location.reload();
  } catch (err) {
    await metroNotice({
      title: "Nie udało się zapisać pliku",
      message: err.message,
    });
  }
}

async function checkAuth(variant) {
  if (!DATA.auth) return;
  const qs = variant ? `?${variant}` : "";
  const res = await fetch(baseUrl() + qs, {
    method: "CHECKAUTH",
  });
  await assertResOK(res);
  $loginBtn.classList.add("hidden");
  $logoutBtn.classList.remove("hidden");
  $userName.textContent = await res.text();
}

async function logout() {
  if (!DATA.auth) return;

  try {
    const res = await fetch("/__routercloud/logout", {
      method: "POST",
      credentials: "same-origin",
    });

    await assertResOK(res);

    location.replace("/__routercloud/login");
  } catch (err) {
    await metroNotice({
      title: "Nie udało się wylogować",
      message: err.message,
    });
  }
}

/**
 * Create a folder
 * @param {string} name
 */
async function createFolder(name) {
  const url = newUrl(name);
  try {
    await checkAuth();
    const res = await fetch(url, {
      method: "MKCOL",
    });
    await assertResOK(res);
    location.href = url;
  } catch (err) {
    await metroNotice({
      title: "Nie można utworzyć folderu",
      message: `Folder „${name}” nie został utworzony.\n\n${err.message}`,
    });
  }
}

async function createFile(name) {
  const url = newUrl(name);
  try {
    await checkAuth();
    const res = await fetch(url, {
      method: "PUT",
      body: "",
    });
    await assertResOK(res);
    location.href = url + "?edit";
  } catch (err) {
    await metroNotice({
      title: "Nie można utworzyć pliku",
      message: `Plik „${name}” nie został utworzony.\n\n${err.message}`,
    });
  }
}

async function addFileEntries(entries, dirs) {
  for (const entry of entries) {
    if (entry.isFile) {
      entry.file(file => {
        new Uploader(file, dirs).upload();
      });
    } else if (entry.isDirectory) {
      const dirReader = entry.createReader();

      const successCallback = entries => {
        if (entries.length > 0) {
          addFileEntries(entries, [...dirs, entry.name]);
          dirReader.readEntries(successCallback);
        }
      };

      dirReader.readEntries(successCallback);
    }
  }
}


function newUrl(name) {
  let url = baseUrl();
  if (!url.endsWith("/")) url += "/";
  url += name.split("/").map(encodeURIComponent).join("/");
  return url;
}

function baseUrl() {
  return location.href.split(/[?#]/)[0];
}

function baseName(url) {
  return decodeURIComponent(url.split("/").filter(v => v.length > 0).slice(-1)[0]);
}

function extName(filename) {
  const dotIndex = filename.lastIndexOf('.');

  if (dotIndex === -1 || dotIndex === 0 || dotIndex === filename.length - 1) {
    return '';
  }

  return filename.substring(dotIndex);
}

function getPathSvg(path_type) {
  switch (path_type) {
    case "Dir":
      return ICONS.dir;
    case "SymlinkFile":
      return ICONS.symlinkFile;
    case "SymlinkDir":
      return ICONS.symlinkDir;
    default:
      return ICONS.file;
  }
}

function formatMtime(mtime) {
  if (!mtime) return "";
  const date = new Date(mtime);
  const year = date.getFullYear();
  const month = padZero(date.getMonth() + 1, 2);
  const day = padZero(date.getDate(), 2);
  const hours = padZero(date.getHours(), 2);
  const minutes = padZero(date.getMinutes(), 2);
  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

function padZero(value, size) {
  return ("0".repeat(size) + value).slice(-1 * size);
}

function formatDirSize(size) {
  const num = size >= MAX_SUBPATHS_COUNT ? `>${MAX_SUBPATHS_COUNT - 1}` : `${size}`;

  let unit;
  if (size === 1) {
    unit = "element";
  } else if (
    size % 10 >= 2 &&
    size % 10 <= 4 &&
    !(size % 100 >= 12 && size % 100 <= 14)
  ) {
    unit = "elementy";
  } else {
    unit = "elementów";
  }

  return ` ${num} ${unit}`;
}

function formatFileSize(size) {
  if (size == null) return [0, "B"];
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  if (size == 0) return [0, "B"];
  const i = parseInt(Math.floor(Math.log(size) / Math.log(1024)));
  const raw = size / Math.pow(1024, i);
  let value;
  if (i > 0 && raw < 999.95) {
    value = Math.round(raw * 10) / 10;
  } else {
    value = Math.round(raw);
  }
  return [value, sizes[i]];
}

function formatDuration(seconds) {
  seconds = Math.ceil(seconds);
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds - h * 3600) / 60);
  const s = seconds - h * 3600 - m * 60;
  return `${padZero(h, 2)}:${padZero(m, 2)}:${padZero(s, 2)}`;
}

function formatPercent(percent) {
  if (percent > 10) {
    return percent.toFixed(1) + "%";
  } else {
    return percent.toFixed(2) + "%";
  }
}

function encodedStr(rawStr) {
  return rawStr.replace(/[\u00A0-\u9999<>\&]/g, function (i) {
    return '&#' + i.charCodeAt(0) + ';';
  });
}

async function assertResOK(res) {
  if (!(res.status >= 200 && res.status < 300)) {
    throw new Error(await res.text() || `Nieprawidłowy status HTTP ${res.status}`);
  }
}

function getEncoding(contentType) {
  const charset = contentType?.split(";")[1];
  if (/charset/i.test(charset)) {
    let encoding = charset.split("=")[1];
    if (encoding) {
      return encoding.toLowerCase();
    }
  }
  return 'utf-8';
}

// Parsing base64 strings with Unicode characters
function decodeBase64(base64String) {
  const binString = atob(base64String);
  const len = binString.length;
  const bytes = new Uint8Array(len);
  const arr = new Uint32Array(bytes.buffer, 0, Math.floor(len / 4));
  let i = 0;
  for (; i < arr.length; i++) {
    arr[i] = binString.charCodeAt(i * 4) |
      (binString.charCodeAt(i * 4 + 1) << 8) |
      (binString.charCodeAt(i * 4 + 2) << 16) |
      (binString.charCodeAt(i * 4 + 3) << 24);
  }
  for (i = i * 4; i < len; i++) {
    bytes[i] = binString.charCodeAt(i);
  }
  return new TextDecoder().decode(bytes);
}
