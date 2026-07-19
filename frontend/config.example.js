// このファイルを config.js としてコピーし、terraform output の値で書き換えてください。
//   cp config.example.js config.js
window.LED_IOT_CONFIG = {
  // terraform output api_base_url の値
  apiBaseUrl: "https://xxxxxxxxxx.execute-api.ap-northeast-1.amazonaws.com/dev",
  // terraform output -raw api_key_value の値
  apiKey: "YOUR_API_KEY_HERE",
};
