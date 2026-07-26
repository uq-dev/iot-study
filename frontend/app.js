(() => {
  const config = window.LED_IOT_CONFIG || {};
  const API_BASE_URL = config.apiBaseUrl;
  const API_KEY = config.apiKey;

  // DOM要素
  const cardAircon = document.getElementById("cardAircon");
  const cardLight = document.getElementById("cardLight");
  
  const airconStatusText = document.getElementById("airconStatusText");
  const lightStatusText = document.getElementById("lightStatusText");
  
  const airconSpinner = document.getElementById("airconSpinner");
  const lightSpinner = document.getElementById("lightSpinner");
  
  const tempValue = document.getElementById("tempValue");
  const tempDownBtn = document.getElementById("tempDownBtn");
  const tempUpBtn = document.getElementById("tempUpBtn");
  
  const modeCoolBtn = document.getElementById("modeCoolBtn");
  const modeHeatBtn = document.getElementById("modeHeatBtn");
  const modeDryBtn = document.getElementById("modeDryBtn");
  const modeFanBtn = document.getElementById("modeFanBtn");
  const modeBtns = [modeCoolBtn, modeHeatBtn, modeDryBtn, modeFanBtn];
  
  const airconPowerBtn = document.getElementById("airconPowerBtn");
  const airconPowerBtnText = document.getElementById("airconPowerBtnText");
  
  const lightFullBtn = document.getElementById("lightFullBtn");
  const lightWarmBtn = document.getElementById("lightWarmBtn");
  const lightEcoBtn = document.getElementById("lightEcoBtn");
  const lightOffBtn = document.getElementById("lightOffBtn");
  
  const syncIndicatorDot = document.getElementById("syncIndicatorDot");
  const syncStatus = document.getElementById("syncStatus");
  const lastSync = document.getElementById("lastSync");
  const errorMessage = document.getElementById("errorMessage");

  // アプリケーション状態の初期値
  let state = {
    aircon: { power: "OFF", temp: 26, mode: "COOL" },
    light: { power: "OFF", mode: "FULL" }
  };

  function setError(message) {
    errorMessage.textContent = message || "";
    if (message) {
      syncIndicatorDot.className = "status-indicator__dot error";
      syncStatus.textContent = "同期エラー";
    } else {
      syncIndicatorDot.className = "status-indicator__dot";
      syncStatus.textContent = "同期完了";
    }
  }

  function setSyncing(isSyncing) {
    if (isSyncing) {
      syncIndicatorDot.className = "status-indicator__dot syncing";
      syncStatus.textContent = "同期中...";
    } else {
      syncIndicatorDot.className = "status-indicator__dot";
      syncStatus.textContent = "同期完了";
      lastSync.textContent = new Date().toLocaleTimeString("ja-JP");
    }
  }

  function renderState() {
    // --- エアコン描画 ---
    const ac = state.aircon;
    cardAircon.dataset.power = ac.power;
    cardAircon.dataset.mode = ac.mode;
    
    airconStatusText.textContent = ac.power === "ON" 
      ? `運転中 (${getModeJpName(ac.mode)} / ${ac.temp}°C)` 
      : "電源 OFF";
    
    tempValue.textContent = ac.temp;
    airconPowerBtnText.textContent = ac.power === "ON" ? "運転停止" : "運転開始";
    
    // 温度調整ボタンの有効無効
    tempDownBtn.disabled = ac.power === "OFF" || ac.temp <= 18;
    tempUpBtn.disabled = ac.power === "OFF" || ac.temp >= 30;
    
    // 運転モードボタンのactive制御
    modeBtns.forEach(btn => {
      if (btn.dataset.mode === ac.mode) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
      btn.disabled = ac.power === "OFF";
    });

    // --- ライト描画 ---
    const lt = state.light;
    cardLight.dataset.power = lt.power;
    cardLight.dataset.mode = lt.mode;
    
    lightStatusText.textContent = lt.power === "ON"
      ? `点灯中 (${getLightModeJpName(lt.mode)})`
      : "電源 OFF";
      
    // パナソニック個別ボタンの有効無効
    lightFullBtn.disabled = false;
    lightWarmBtn.disabled = false;
    lightEcoBtn.disabled = false;
    lightOffBtn.disabled = lt.power === "OFF";
  }

  function getModeJpName(mode) {
    const names = { COOL: "冷房", HEAT: "暖房", DRY: "除湿", FAN: "送風" };
    return names[mode] || mode;
  }

  function getLightModeJpName(mode) {
    const names = { FULL: "全灯", WARM: "調光", ECO: "常夜灯" };
    return names[mode] || mode;
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
    setSyncing(true);
    try {
      const data = await apiRequest("/appliances/state", { method: "GET" });
      state = data;
      renderState();
    } catch (err) {
      setError(err.message);
    } finally {
      setSyncing(false);
    }
  }

  async function updateState(payload, spinner) {
    setError("");
    setSyncing(true);
    if (spinner) spinner.classList.add("active");
    
    // UI操作を一時的にロック
    toggleControls(true);
    
    try {
      const data = await apiRequest("/appliances/state", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      // レスポンスデータをローカル状態にマージ
      if (data.aircon) state.aircon = { ...state.aircon, ...data.aircon };
      if (data.light) state.light = { ...state.light, ...data.light };
      renderState();
    } catch (err) {
      setError(err.message);
    } finally {
      setSyncing(false);
      if (spinner) spinner.classList.remove("active");
      toggleControls(false);
    }
  }

  function toggleControls(disabled) {
    const allButtons = document.querySelectorAll("button");
    allButtons.forEach(btn => {
      if (disabled) {
        btn.dataset.prevDisabled = btn.disabled;
        btn.disabled = true;
      } else {
        btn.disabled = btn.dataset.prevDisabled === "true";
      }
    });
    // ロック解除後、状態に応じた無効状態を再描画
    if (!disabled) {
      renderState();
    }
  }

  // --- エアコンイベントリスナー ---
  airconPowerBtn.addEventListener("click", () => {
    const nextPower = state.aircon.power === "ON" ? "OFF" : "ON";
    updateState({ aircon: { power: nextPower } }, airconSpinner);
  });

  tempDownBtn.addEventListener("click", () => {
    if (state.aircon.temp > 18) {
      updateState({ aircon: { temp: state.aircon.temp - 1 } }, airconSpinner);
    }
  });

  tempUpBtn.addEventListener("click", () => {
    if (state.aircon.temp < 30) {
      updateState({ aircon: { temp: state.aircon.temp + 1 } }, airconSpinner);
    }
  });

  modeBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      updateState({ aircon: { mode: btn.dataset.mode } }, airconSpinner);
    });
  });

  // --- ライトイベントリスナー ---
  lightFullBtn.addEventListener("click", () => {
    updateState({ light: { power: "ON", mode: "FULL" } }, lightSpinner);
  });

  lightWarmBtn.addEventListener("click", () => {
    updateState({ light: { power: "ON", mode: "WARM" } }, lightSpinner);
  });

  lightEcoBtn.addEventListener("click", () => {
    updateState({ light: { power: "ON", mode: "ECO" } }, lightSpinner);
  });

  lightOffBtn.addEventListener("click", () => {
    updateState({ light: { power: "OFF" } }, lightSpinner);
  });

  // 初期読み込み
  fetchState();
})();
