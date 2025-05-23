# IoT 節點編排介面

一個基於純 HTML + JavaScript 的拖拉式 IoT 節點編排介面，讓您可以視覺化地設計和執行 IoT 設備之間的通信流程。

## 功能特色

- 🎯 **視覺化節點編排**: 拖拉式介面，直觀地創建 IoT 設備連線
- 📱 **多種節點類型**: 支援 IoT 裝置、發布節點、訂閱節點、函式節點
- 🔗 **動態連線**: 滑鼠拖拉創建節點間的連線關係
- ⚙️ **屬性編輯**: 即時編輯節點屬性和連線設定
- 🚀 **實際執行**: 基於 MQTT 協議的真實 IoT 設備通信
- 💾 **匯出入功能**: 儲存和載入流程設計

## 快速開始

### 1. 安裝依賴
```bash
npm install
```

### 2. 啟動服務器
```bash
npm start
```

### 3. 開啟瀏覽器
訪問 `http://localhost:3000/flow-editor` 開始使用流程編輯器

## 使用說明

### 節點類型

1. **📱 IoT 裝置**: 代表一個 MQTT 連接的 IoT 設備
   - 設定裝置 ID、MQTT Broker URL、帳號密碼
   - 可以接收和發送 MQTT 訊息

2. **📡 發布節點**: 發送 MQTT 訊息到指定主題
   - 設定目標主題、負載內容、QoS 等級
   - 支援同步和非同步模式

3. **📥 訂閱節點**: 訂閱 MQTT 主題並處理收到的訊息
   - 設定訂閱主題模式
   - 自定義處理函式

4. **⚙️ 函式節點**: 處理和轉換資料
   - 編寫 JavaScript 函式處理輸入資料
   - 可用於資料格式轉換、邏輯運算等

### 操作流程

1. **添加節點**: 點擊左側工具面板的按鈕添加不同類型的節點
2. **設定屬性**: 點擊節點，在右側屬性面板編輯節點設定
3. **創建連線**: 從節點的橘色輸出埠拖拉到另一個節點的綠色輸入埠
4. **執行流程**: 點擊上方工具列的「▶️ 執行」按鈕啟動 IoT 流程
5. **查看日誌**: 點擊「📋 日誌」按鈕查看執行日誌

### 演示範例

左側面板提供兩個預設演示範例：
- **🚀 基本範例**: 展示感測器 → 資料處理 → 控制器的基本流程
- **🌡️ 感測器監控**: 多感測器資料聚合和警報系統

## 技術架構

### 前端
- **純 Vanilla JavaScript**: 不依賴任何前端框架
- **SVG 連線繪製**: 使用 SVG 元素繪制節點間連線
- **Pointer Events**: 實現跨平台的拖拉操作
- **模組化設計**: ES6 模組系統

### 後端
- **Express.js**: 靜態檔案服務器
- **MQTT.js**: 瀏覽器端 MQTT 客戶端
- **WebSocket 支援**: 透過 WebSocket 連接 MQTT Broker

### IoT 通信
- **MQTT 協議**: 輕量級的 IoT 通信協議
- **預設 Broker**: `wss://mqtt-edu.webduino.io/mqtt`
- **自動重連**: 支援斷線自動重連機制

## 資料結構

### 流程資料
```javascript
{
  nodes: [
    {
      id: "n1",
      type: "device",
      x: 100,
      y: 150,
      data: {
        deviceId: "sensor01",
        brokerUrl: "wss://mqtt-edu.webduino.io/mqtt",
        username: "hsh2025",
        password: "hsh2025"
      }
    }
  ],
  edges: [
    {
      id: "e1", 
      sourceId: "n1",
      targetId: "n2",
      action: "trigger",
      mode: "async"
    }
  ]
}
```

## API 參考

### IoTDevice 類
```javascript
// 創建設備實例
const device = new IoTDevice('deviceId');

// 連接 MQTT Broker  
await device.connect();

// 發布訊息
device.pub('target.action', { data: 'value' });

// 同步發布
const response = await device.pubSync('target.action', { data: 'value' });

// 註冊處理器
device.proc('action', async (message) => {
  return { processed: true };
});

// 斷開連線
await device.disconnect();
```

## 開發

### 專案結構
```
hsh-demo/
├── public/
│   ├── flow-editor.html      # 流程編輯器頁面
│   ├── flow-editor.js        # 編輯器核心邏輯  
│   ├── iotDevice.js          # IoT 設備類
│   └── index.html            # 原始測試頁面
├── server.js                 # Express 服務器
├── package.json             # 專案設定
└── README.md               # 說明文件
```

### 擴展功能

1. **自定義節點類型**: 修改 `getDefaultNodeData()` 和相關渲染函式
2. **新增連線樣式**: 擴展 CSS 和 SVG 連線渲染邏輯  
3. **資料持久化**: 整合資料庫儲存流程設計
4. **即時協作**: 加入 WebSocket 支援多用戶協作編輯

## 授權

ISC 授權

## 貢獻

歡迎提交 Issue 和 Pull Request！

---

*基於您提供的設計思路實現的拖拉式 IoT 節點編排介面* # hsh-demo
