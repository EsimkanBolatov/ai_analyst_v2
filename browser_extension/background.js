const DEFAULT_SETTINGS = {
  apiBaseUrl: "http://localhost:8010/api/v1",
  continuousProtection: false
};

const CONTEXT_MENU_ID = "ai-analyst-check-selection";

function storageGet(keys) {
  return new Promise((resolve) => chrome.storage.sync.get(keys, resolve));
}

function storageSet(values) {
  return new Promise((resolve) => chrome.storage.sync.set(values, resolve));
}

function queryTabs(queryInfo) {
  return new Promise((resolve) => chrome.tabs.query(queryInfo, resolve));
}

function sendMessageToTab(tabId, message) {
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, message, () => {
      resolve();
    });
  });
}

async function getSettings() {
  const stored = await storageGet(DEFAULT_SETTINGS);
  return { ...DEFAULT_SETTINGS, ...stored };
}

async function ensureSettings() {
  const current = await storageGet(DEFAULT_SETTINGS);
  const next = { ...DEFAULT_SETTINGS, ...current };
  await storageSet(next);
  return next;
}

function inferDataType(rawValue) {
  const value = String(rawValue || "").trim();
  if (!value) {
    return "text";
  }

  if (/^(https?:\/\/|www\.)/i.test(value)) {
    return "url";
  }

  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
    return "email";
  }

  const digits = value.replace(/\D+/g, "");
  if (digits.length >= 7) {
    return "phone";
  }

  return "text";
}

async function callApi(path, payload) {
  const settings = await getSettings();
  const response = await fetch(`${settings.apiBaseUrl}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    let detail = `API request failed with status ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch (_error) {
      // ignore parse failure
    }
    throw new Error(detail);
  }

  return response.json();
}

async function checkSingleValue(rawValue, explicitType) {
  const value = String(rawValue || "").trim();
  const dataType = explicitType || inferDataType(value);
  const result = await callApi("/fraud/check", {
    data_type: dataType,
    value
  });

  return {
    dataType,
    value,
    result
  };
}

async function checkBatch(items) {
  const sanitized = (items || [])
    .map((item) => ({
      data_type: item.dataType,
      value: String(item.value || "").trim()
    }))
    .filter((item) => item.value);

  if (sanitized.length === 0) {
    return { results: [] };
  }

  return callApi("/fraud/check-batch", { items: sanitized });
}

async function triggerScanOnActiveTab() {
  const tabs = await queryTabs({ active: true, currentWindow: true });
  const [tab] = tabs;
  if (tab && tab.id) {
    await sendMessageToTab(tab.id, { type: "TRIGGER_SCAN" });
  }
}

async function ensureContextMenu() {
  await new Promise((resolve) => chrome.contextMenus.removeAll(resolve));
  chrome.contextMenus.create({
    id: CONTEXT_MENU_ID,
    title: "Проверить в AI-Analyst",
    contexts: ["selection"]
  });
}

function formatContextMessage(dataType, apiResponse) {
  if (apiResponse.is_blacklisted) {
    const category = apiResponse.matched_entry?.category || "Blacklist";
    return {
      severity: "danger",
      message: `Опасно: ${dataType} найден в blacklist (${category}).`
    };
  }

  return {
    severity: "safe",
    message: `Совпадений по типу "${dataType}" не найдено.`
  };
}

chrome.runtime.onInstalled.addListener(() => {
  void ensureSettings();
  void ensureContextMenu();
});

chrome.runtime.onStartup.addListener(() => {
  void ensureContextMenu();
});

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status !== "complete" || !tab.url || !/^https?:/i.test(tab.url)) {
    return;
  }

  const settings = await getSettings();
  if (settings.continuousProtection) {
    await sendMessageToTab(tabId, { type: "TRIGGER_SCAN" });
  }
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== CONTEXT_MENU_ID || !info.selectionText || !tab?.id) {
    return;
  }

  void (async () => {
    try {
      const { dataType, result } = await checkSingleValue(info.selectionText);
      const contextMessage = formatContextMessage(dataType, result);
      await sendMessageToTab(tab.id, {
        type: "SHOW_CONTEXT_RESULT",
        ...contextMessage,
        value: info.selectionText
      });
    } catch (error) {
      await sendMessageToTab(tab.id, {
        type: "SHOW_CONTEXT_RESULT",
        severity: "error",
        message: error instanceof Error ? error.message : "Не удалось выполнить проверку."
      });
    }
  })();
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  void (async () => {
    switch (message?.type) {
      case "GET_SETTINGS":
        sendResponse({ ok: true, data: await getSettings() });
        return;
      case "SET_SETTINGS": {
        const nextSettings = {
          ...DEFAULT_SETTINGS,
          ...(message.settings || {})
        };
        await storageSet(nextSettings);
        sendResponse({ ok: true, data: nextSettings });
        return;
      }
      case "CHECK_VALUE": {
        const data = await checkSingleValue(message.value, message.dataType);
        sendResponse({ ok: true, data });
        return;
      }
      case "CHECK_BATCH": {
        const data = await checkBatch(message.items || []);
        sendResponse({ ok: true, data });
        return;
      }
      case "RESCAN_ACTIVE_TAB":
        await triggerScanOnActiveTab();
        sendResponse({ ok: true, data: { triggered: true } });
        return;
      default:
        sendResponse({ ok: false, error: "Unsupported message type." });
    }
  })().catch((error) => {
    sendResponse({
      ok: false,
      error: error instanceof Error ? error.message : "Unexpected extension error."
    });
  });

  return true;
});
