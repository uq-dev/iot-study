(() => {
  const config = window.LED_IOT_CONFIG || {};
  const API_BASE_URL = config.apiBaseUrl;
  const API_KEY = config.apiKey;

  const bulb = document.getElementById("bulb");
  const bulbLabel = document.getElementById("bulbLabel");
  const toggleBtn = document.getElementById("toggleBtn");
  const toggleBtnLabel = document.getElementById("toggleBtnLabel");
  const lastSync = document.getElementById("lastSync");
  const errorMessage = document.getElementById("errorMessage");

  let currentState = null; // "ON" | "OFF"

  function setError(message) {
    errorMessage.textContent = message || "";
  }

  function renderState(state) {
    currentState = state;
    const isOn = state === "ON";
    bulb.dataset.state = isOn ? "on" : "off";
    bulbLabel.textContent = isOn ? "LED: ON" : "LED: OFF";
    toggleBtnLabel.textContent = isOn ? "TURN OFF" : "TURN ON";
    lastSync.textContent = new Date().toLocaleTimeString("ja-JP");
    toggleBtn.disabled = false;
  }

  async function apiRequest(path, options = {}) {
    if (!API_BASE_URL || !API_KEY) {
      throw new Error("config.js が未設定です（config.example.js を参考に作成してください）");
    }
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        ...(options.headers || {}),
      },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.message || `リクエストに失敗しました (HTTP ${response.status})`);
    }
    return data;
  }

  async function fetchState() {
    setError("");
    try {
      const data = await apiRequest("/led/state", { method: "GET" });
      renderState(data.state);
    } catch (err) {
      setError(err.message);
      bulbLabel.textContent = "取得エラー";
    }
  }

  async function toggleState() {
    if (!currentState) return;
    const nextState = currentState === "ON" ? "OFF" : "ON";
    setError("");
    toggleBtn.disabled = true;
    try {
      const data = await apiRequest("/led/state", {
        method: "POST",
        body: JSON.stringify({ state: nextState }),
      });
      renderState(data.state);
    } catch (err) {
      setError(err.message);
      toggleBtn.disabled = false;
    }
  }

  toggleBtn.addEventListener("click", toggleState);

  fetchState();
})();
