# HSH Demo 專案

## 專案概述

這是一個整合型的 IoT 示範專案，結合了 **溫度監控儀表板**、**MicroPython 硬體控制**、**MQTT 通訊** 和 **網頁遊戲** 等功能。專案主要用於展示物聯網設備與網頁應用程式的整合應用。

## 主要功能

### 🌡️ 溫度監控儀表板
- **視覺化溫度顯示**：具有半圓形儀表板的直觀溫度顯示介面
- **即時溫度監控**：支援即時溫度數據更新和狀態顯示
- **溫度區間標示**：
  - 冷態：0-20°C (藍色)
  - 適溫：21-40°C (綠色)
  - 溫熱：41-60°C (橙色)
  - 高溫：61-80°C (紅色)
- **互動控制**：
  - 手動溫度調節滑桿
  - 自動溫度模擬功能
  - 模擬開始/停止控制

### 📡 MQTT 物聯網通訊
- **MQTT 連線管理**：自動連線至教育用 MQTT Broker
- **雙向通訊**：支援發布/訂閱模式
- **同步/非同步通訊**：
  - `pub()` - 非同步發布訊息
  - `pubSync()` - 同步請求回覆
  - `proc()` - 註冊訊息處理器
- **設備識別**：每個設備具有唯一 ID 和 MQTT 客戶端 ID
- **錯誤處理**：完整的連線錯誤處理和逾時機制

### 🎮 網頁遊戲
- **Mario 遊戲**：經典的馬里奧風格平台遊戲
- **Hit Blocks 遊戲**：方塊點擊遊戲

### 🔧 MicroPython 硬體控制
提供完整的 MicroPython 函式庫，支援各種硬體模組：

#### 感測器模組
- **DHT11**：溫濕度感測器
- **超音波感測器**：距離測量
- **聲音感測器**：音量檢測
- **震動感測器**：震動檢測
- **類比感測器**：一般類比訊號讀取

#### 控制模組
- **伺服馬達 (SG90)**：精確角度控制
- **LED 控制**：燈光效果
- **顯示器控制**：螢幕顯示功能

#### 通訊模組
- **WiFi 連線**：無線網路連接
- **MQTT 通訊**：物聯網訊息傳遞
- **ESP-NOW**：ESP32/ESP8266 直接通訊
- **網頁伺服器**：HTTP 服務功能

## 技術架構

### 前端技術
- **HTML5 Canvas**：儀表板繪圖和遊戲渲染
- **JavaScript ES6+**：模組化程式設計
- **CSS3**：現代化響應式設計
- **MQTT.js**：瀏覽器端 MQTT 客戶端

### 後端技術
- **Node.js**：伺服器運行環境
- **Express.js**：Web 應用框架
- **MQTT 客戶端**：物聯網通訊

### 硬體支援
- **MicroPython**：嵌入式 Python 運行環境
- **Webduino 函式庫**：硬體抽象層
- **ESP32/ESP8266**：主要支援的開發板

### 依賴套件
```json
{
  "express": "^5.1.0",    // Web 伺服器框架
  "mqtt": "^5.13.0",      // MQTT 通訊協定
  "uuid": "^11.1.0",      // 唯一識別碼產生
  "dotenv": "^16.5.0"     // 環境變數管理
}
```

## 安裝與使用

### 環境需求
- Node.js (v18 或以上)
- npm 或 yarn
- 現代化瀏覽器 (支援 WebSocket)

### 安裝步驟

1. **複製專案**
```bash
git clone <repository-url>
cd hsh-demo
```

2. **安裝依賴**
```bash
npm install
```

3. **啟動開發伺服器**
```bash
npm run dev  # 開發模式 (含自動重新載入)
# 或
npm start    # 正式模式
```

4. **開啟瀏覽器**
```
http://localhost:3000
```

### MicroPython 使用

1. **上傳函式庫**
   將 `micropython/lib/webduino/` 資料夾上傳至你的 ESP32/ESP8266 設備

2. **執行範例**
   參考 `micropython/demo/` 目錄中的範例程式：
   - `demo-06-dht11.py` - 溫濕度感測器
   - `demo-05-ultrasonic.py` - 超音波測距
   - `demo-02-sound.py` - 聲音感測
   - `demo-04-servo.py` - 伺服馬達控制

## MQTT 通訊協定

### 連線資訊
- **Broker**: wss://mqtt-edu.webduino.io/mqtt
- **帳號**: hsh2025
- **密碼**: hsh2025

### 主題格式
- **請求主題**: `{targetDeviceId}/{action}`
- **回覆主題**: `{requesterDeviceId}/reply/{requestId}`

### 訊息格式
```json
{
  "requestId": "uuid-v4",
  "from": "deviceId",
  "payload": { ... }
}
```

## 專案結構

```
hsh-demo/
├── public/                 # 前端靜態檔案
│   ├── index.html         # 溫度儀表板主頁
│   ├── iotDevice.js       # IoT 設備通訊類別
│   └── game/              # 網頁遊戲
│       ├── mario.html     # Mario 遊戲
│       └── hit_blocks.html # 方塊遊戲
├── micropython/           # MicroPython 相關檔案
│   ├── lib/webduino/     # 硬體控制函式庫
│   └── demo/             # 使用範例
├── prompt/               # 技術文件
│   ├── iotDevice.md      # IoT 設備 API 文件
│   └── webbit_api.md     # Webbit 開發板 API
├── server.js             # Express 伺服器
└── package.json          # 專案配置檔
```

## 開發指南

### 新增 IoT 設備
```javascript
// 建立新設備
const device = new IoTDevice('your-device-id');
await device.connect();

// 註冊訊息處理器
await device.proc('sensor-data', async (msg) => {
    console.log('接收到感測器資料:', msg.payload);
    return { status: 'received' };
});

// 發送訊息
device.pub('target-device.action', { data: 'hello' });

// 同步請求
const response = await device.pubSync('target-device.getData', {});
```

### 自訂硬體模組
參考 `micropython/lib/webduino/` 中的現有模組，建立新的硬體控制類別。

## 授權條款

ISC License

## 貢獻

歡迎提交 Issue 和 Pull Request 來改善這個專案。
