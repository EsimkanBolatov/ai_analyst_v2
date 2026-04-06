(function () {
  const SETTINGS_DEFAULTS = {
    continuousProtection: false
  };
  const HIGHLIGHT_CLASS = "ai-analyst-flagged";
  const BADGE_ID = "ai-analyst-page-badge";
  const TOAST_ID = "ai-analyst-toast";
  const MAX_BATCH_ITEMS = 150;
  const PHONE_REGEX = /(?:\+?\d[\d()\-\s]{7,}\d)/g;

  let continuousProtection = false;
  let observer = null;
  let scanTimeout = null;

  function storageGet(keys) {
    return new Promise((resolve) => chrome.storage.sync.get(keys, resolve));
  }

  function sendRuntimeMessage(message) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        if (!response?.ok) {
          reject(new Error(response?.error || "Unknown extension error."));
          return;
        }
        resolve(response.data);
      });
    });
  }

  function ensureStyles() {
    if (document.getElementById("ai-analyst-extension-styles")) {
      return;
    }

    const style = document.createElement("style");
    style.id = "ai-analyst-extension-styles";
    style.textContent = `
      .${HIGHLIGHT_CLASS} {
        outline: 2px solid #b80000 !important;
        box-shadow: 0 0 0 4px rgba(184, 0, 0, 0.12) !important;
        position: relative !important;
        border-radius: 6px !important;
        background: rgba(184, 0, 0, 0.08) !important;
      }
      .${HIGHLIGHT_CLASS}::after {
        content: attr(data-ai-analyst-label);
        position: absolute;
        top: -12px;
        right: -2px;
        background: #111111;
        color: #f4f1ea;
        padding: 4px 8px;
        font-size: 10px;
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        border-radius: 999px;
        z-index: 2147483647;
      }
      #${BADGE_ID} {
        position: fixed;
        right: 16px;
        bottom: 16px;
        z-index: 2147483647;
        background: #111111;
        color: #f4f1ea;
        padding: 10px 14px;
        border-radius: 999px;
        font: 600 12px/1.2 "IBM Plex Sans", "Segoe UI", sans-serif;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        box-shadow: 0 18px 40px rgba(17, 17, 17, 0.28);
      }
      #${TOAST_ID} {
        position: fixed;
        right: 16px;
        top: 16px;
        z-index: 2147483647;
        max-width: 360px;
        padding: 14px 16px;
        border-radius: 18px;
        background: #111111;
        color: #f4f1ea;
        font: 500 13px/1.45 "IBM Plex Sans", "Segoe UI", sans-serif;
        box-shadow: 0 18px 40px rgba(17, 17, 17, 0.28);
      }
      #${TOAST_ID}[data-severity="danger"] { background: #8f0000; }
      #${TOAST_ID}[data-severity="safe"] { background: #111111; }
      #${TOAST_ID}[data-severity="error"] { background: #4a4a4a; }
    `;
    document.documentElement.appendChild(style);
  }

  function clearHighlights() {
    document.querySelectorAll(`.${HIGHLIGHT_CLASS}`).forEach((element) => {
      element.classList.remove(HIGHLIGHT_CLASS);
      element.removeAttribute("data-ai-analyst-label");
      element.removeAttribute("data-ai-analyst-flagged");
    });
    const badge = document.getElementById(BADGE_ID);
    if (badge) {
      badge.remove();
    }
  }

  function showBadge(flaggedCount, scannedCount) {
    let badge = document.getElementById(BADGE_ID);
    if (!badge) {
      badge = document.createElement("div");
      badge.id = BADGE_ID;
      document.documentElement.appendChild(badge);
    }
    badge.textContent = `${flaggedCount} flagged / ${scannedCount} scanned`;
  }

  function showToast(message, severity) {
    let toast = document.getElementById(TOAST_ID);
    if (!toast) {
      toast = document.createElement("div");
      toast.id = TOAST_ID;
      document.documentElement.appendChild(toast);
    }
    toast.textContent = message;
    toast.dataset.severity = severity || "safe";
    window.clearTimeout(showToast.timeoutId);
    showToast.timeoutId = window.setTimeout(() => {
      toast.remove();
    }, 4200);
  }
  showToast.timeoutId = 0;

  function normalizeCandidateValue(value) {
    return String(value || "").trim();
  }

  function addCandidate(candidateMap, dataType, value, element) {
    const normalizedValue = normalizeCandidateValue(value);
    if (!normalizedValue || !element) {
      return;
    }

    const key = `${dataType}:${normalizedValue}`;
    if (!candidateMap.has(key)) {
      candidateMap.set(key, {
        dataType,
        value: normalizedValue,
        elements: new Set()
      });
    }
    candidateMap.get(key).elements.add(element);
  }

  function shouldIgnoreTextNode(parentElement) {
    if (!parentElement) {
      return true;
    }
    const tagName = parentElement.tagName;
    return [
      "SCRIPT",
      "STYLE",
      "NOSCRIPT",
      "TEXTAREA",
      "INPUT",
      "SELECT",
      "OPTION"
    ].includes(tagName);
  }

  function collectCandidates() {
    const candidateMap = new Map();

    document.querySelectorAll("a[href]").forEach((anchor) => {
      const href = anchor.href || anchor.getAttribute("href");
      if (/^https?:/i.test(href || "")) {
        addCandidate(candidateMap, "url", href, anchor);
      }
    });

    const walker = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_TEXT);
    let node = walker.nextNode();
    while (node) {
      const parentElement = node.parentElement;
      if (!shouldIgnoreTextNode(parentElement)) {
        const text = node.nodeValue || "";
        let match = PHONE_REGEX.exec(text);
        while (match) {
          addCandidate(candidateMap, "phone", match[0], parentElement);
          match = PHONE_REGEX.exec(text);
        }
        PHONE_REGEX.lastIndex = 0;
      }
      node = walker.nextNode();
    }

    return Array.from(candidateMap.values()).slice(0, MAX_BATCH_ITEMS);
  }

  function applyResults(candidates, results) {
    clearHighlights();
    if (!Array.isArray(results) || results.length === 0) {
      return;
    }

    const lookup = new Map();
    results.forEach((item) => {
      lookup.set(`${item.data_type}:${item.value}`, item);
    });

    let flaggedCount = 0;
    candidates.forEach((candidate) => {
      const key = `${candidate.dataType}:${candidate.value}`;
      const result = lookup.get(key);
      if (!result || !result.is_blacklisted) {
        return;
      }

      const label = result.matched_entry?.category || "Fraud";
      candidate.elements.forEach((element) => {
        if (element.dataset.aiAnalystFlagged === "1") {
          return;
        }
        element.classList.add(HIGHLIGHT_CLASS);
        element.dataset.aiAnalystFlagged = "1";
        element.dataset.aiAnalystLabel = label;
        element.title = `AI-Analyst: ${label}`;
        flaggedCount += 1;
      });
    });

    if (flaggedCount > 0) {
      showBadge(flaggedCount, candidates.length);
    }
  }

  async function scanPage() {
    if (!continuousProtection) {
      clearHighlights();
      return;
    }

    const candidates = collectCandidates();
    if (candidates.length === 0) {
      clearHighlights();
      return;
    }

    try {
      const data = await sendRuntimeMessage({
        type: "CHECK_BATCH",
        items: candidates.map((candidate) => ({
          dataType: candidate.dataType,
          value: candidate.value
        }))
      });
      applyResults(candidates, data.results || []);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Batch check failed.", "error");
    }
  }

  function scheduleScan() {
    window.clearTimeout(scanTimeout);
    scanTimeout = window.setTimeout(() => {
      void scanPage();
    }, 700);
  }

  function startObserver() {
    if (observer) {
      return;
    }
    observer = new MutationObserver(() => {
      scheduleScan();
    });
    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
      characterData: true
    });
  }

  function stopObserver() {
    if (observer) {
      observer.disconnect();
      observer = null;
    }
  }

  async function init() {
    ensureStyles();
    const settings = await storageGet(SETTINGS_DEFAULTS);
    continuousProtection = Boolean(settings.continuousProtection);
    if (continuousProtection) {
      startObserver();
      await scanPage();
    }
  }

  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName !== "sync" || !changes.continuousProtection) {
      return;
    }

    continuousProtection = Boolean(changes.continuousProtection.newValue);
    if (continuousProtection) {
      startObserver();
      scheduleScan();
      showToast("Непрерывная защита включена.", "safe");
    } else {
      stopObserver();
      clearHighlights();
      showToast("Непрерывная защита выключена.", "safe");
    }
  });

  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type === "TRIGGER_SCAN") {
      scheduleScan();
    }
    if (message?.type === "SHOW_CONTEXT_RESULT") {
      showToast(message.message || "Проверка завершена.", message.severity || "safe");
    }
  });

  void init();
})();
