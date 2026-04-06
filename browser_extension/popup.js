const DEFAULT_SETTINGS = {
  apiBaseUrl: "http://localhost:8010/api/v1",
  continuousProtection: false
};

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

function showSettingsStatus(message) {
  document.getElementById("settings-status").textContent = message;
  window.clearTimeout(showSettingsStatus.timeoutId);
  showSettingsStatus.timeoutId = window.setTimeout(() => {
    document.getElementById("settings-status").textContent = "";
  }, 2500);
}
showSettingsStatus.timeoutId = 0;

function showResult({ severity, title, body }) {
  const panel = document.getElementById("result-panel");
  panel.classList.remove("hidden", "safe", "danger", "error");
  panel.classList.add(severity);
  document.getElementById("result-title").textContent = title;
  document.getElementById("result-body").textContent = body;
}

function formatCheckResult(data) {
  if (data.result.is_blacklisted) {
    return {
      severity: "danger",
      title: `Совпадение: ${data.dataType}`,
      body: `Найдено в blacklist. Категория: ${data.result.matched_entry?.category || "Fraud"}`
    };
  }

  return {
    severity: "safe",
    title: `Совпадений нет: ${data.dataType}`,
    body: "По текущему blacklist значение не найдено."
  };
}

async function loadSettings() {
  const settings = await sendRuntimeMessage({ type: "GET_SETTINGS" });
  document.getElementById("api-base-url").value = settings.apiBaseUrl || DEFAULT_SETTINGS.apiBaseUrl;
  document.getElementById("continuous-toggle").checked = Boolean(settings.continuousProtection);
}

async function saveSettings() {
  const nextSettings = {
    apiBaseUrl: document.getElementById("api-base-url").value.trim() || DEFAULT_SETTINGS.apiBaseUrl,
    continuousProtection: document.getElementById("continuous-toggle").checked
  };
  await sendRuntimeMessage({ type: "SET_SETTINGS", settings: nextSettings });
  showSettingsStatus("Настройки сохранены.");
  if (nextSettings.continuousProtection) {
    await sendRuntimeMessage({ type: "RESCAN_ACTIVE_TAB" });
  }
}

async function runManualCheck() {
  const value = document.getElementById("manual-value").value.trim();
  if (!value) {
    showResult({
      severity: "error",
      title: "Нет данных",
      body: "Введите ссылку, номер, email или текст для проверки."
    });
    return;
  }

  try {
    const data = await sendRuntimeMessage({ type: "CHECK_VALUE", value });
    showResult(formatCheckResult(data));
  } catch (error) {
    showResult({
      severity: "error",
      title: "Ошибка проверки",
      body: error instanceof Error ? error.message : "Unexpected extension error."
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  void loadSettings();

  document.getElementById("save-settings-button").addEventListener("click", () => {
    void saveSettings();
  });

  document.getElementById("check-button").addEventListener("click", () => {
    void runManualCheck();
  });

  document.getElementById("rescan-button").addEventListener("click", () => {
    void sendRuntimeMessage({ type: "RESCAN_ACTIVE_TAB" })
      .then(() => showSettingsStatus("Сканирование запущено."))
      .catch((error) => showSettingsStatus(error instanceof Error ? error.message : "Не удалось запустить сканирование."));
  });

  document.getElementById("continuous-toggle").addEventListener("change", () => {
    void saveSettings();
  });
});
