// 引入 IoT 設備類
import { IoTDevice } from './iotDevice.js';

// 全局狀態
const flow = {
    nodes: [],    // { id, type, x, y, data }
    edges: []     // { id, sourceId, targetId, action, mode }
};

// 節點產生唯一 ID
let nextId = 1;
function genId() { 
    return `n${nextId++}`; 
}

// DOM 元素
const canvas = document.getElementById('canvas');
const connectionLayer = document.getElementById('connection-layer');
const inspector = document.getElementById('inspector-content');
const logPanel = document.getElementById('log-panel');
const logContent = document.getElementById('log-content');

// 執行狀態
let isRunning = false;
let devices = new Map(); // deviceId -> IoTDevice instance
let selectedItem = null; // 當前選中的項目
let dragState = {
    isDragging: false,
    dragElement: null,
    offsetX: 0,
    offsetY: 0
};

// 連線狀態
let connectionState = {
    isConnecting: false,
    sourceNode: null,
    sourcePort: null,
    tempLine: null
};

// 初始化
document.addEventListener('DOMContentLoaded', init);

function init() {
    setupEventListeners();
    log('節點編排介面已初始化', 'info');
}

// 設置事件監聽器
function setupEventListeners() {
    // 工具面板按鈕
    document.querySelectorAll('.palette-button').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const nodeType = e.target.dataset.type;
            if (nodeType) {
                createNode(nodeType);
            }
        });
    });

    // 演示按鈕
    document.getElementById('demo-basic')?.addEventListener('click', createBasicDemo);
    document.getElementById('demo-sensor')?.addEventListener('click', createSensorDemo);

    // 工具列按鈕
    document.getElementById('run-btn').addEventListener('click', runFlow);
    document.getElementById('stop-btn').addEventListener('click', stopFlow);
    document.getElementById('clear-btn').addEventListener('click', clearFlow);
    document.getElementById('save-btn').addEventListener('click', saveFlow);
    document.getElementById('load-btn').addEventListener('click', loadFlow);
    document.getElementById('log-btn').addEventListener('click', toggleLog);

    // 畫布事件
    canvas.addEventListener('click', (e) => {
        if (e.target === canvas) {
            clearSelection();
        }
    });

    // 連線相關事件
    setupConnectionEvents();
}

// 創建節點
function createNode(type) {
    const nodeId = genId();
    const node = {
        id: nodeId,
        type: type,
        x: 100 + Math.random() * 200,
        y: 100 + Math.random() * 200,
        data: getDefaultNodeData(type)
    };

    flow.nodes.push(node);
    renderNode(node);
    log(`已創建 ${getNodeTypeName(type)} 節點: ${nodeId}`, 'info');
}

// 獲取節點預設資料
function getDefaultNodeData(type) {
    switch (type) {
        case 'device':
            return {
                deviceId: '',
                brokerUrl: 'wss://mqtt-edu.webduino.io/mqtt',
                username: 'hsh2025',
                password: 'hsh2025',
                handlers: []
            };
        case 'publish':
            return {
                topic: '',
                payload: '{}',
                qos: 0,
                mode: 'async'
            };
        case 'subscribe':
            return {
                topic: '',
                handler: 'function(message) {\n  console.log(message);\n}'
            };
        case 'function':
            return {
                name: '',
                code: 'function process(input) {\n  return input;\n}'
            };
        default:
            return {};
    }
}

// 獲取節點類型名稱
function getNodeTypeName(type) {
    const names = {
        device: 'IoT 裝置',
        publish: '發布節點',
        subscribe: '訂閱節點',
        function: '函式節點'
    };
    return names[type] || type;
}

// 渲染節點
function renderNode(node) {
    const nodeEl = document.createElement('div');
    nodeEl.className = `node ${node.type}`;
    nodeEl.dataset.id = node.id;
    nodeEl.style.left = `${node.x}px`;
    nodeEl.style.top = `${node.y}px`;

    // 節點內容
    const header = document.createElement('div');
    header.className = 'node-header';
    header.textContent = getNodeTypeName(node.type);

    const content = document.createElement('div');
    content.className = 'node-content';
    content.textContent = getNodeDisplayText(node);

    nodeEl.appendChild(header);
    nodeEl.appendChild(content);

    // 添加連接埠
    if (node.type !== 'publish') {
        const inputPort = document.createElement('div');
        inputPort.className = 'port input';
        inputPort.dataset.nodeId = node.id;
        inputPort.dataset.portType = 'input';
        nodeEl.appendChild(inputPort);
    }

    if (node.type !== 'subscribe') {
        const outputPort = document.createElement('div');
        outputPort.className = 'port output';
        outputPort.dataset.nodeId = node.id;
        outputPort.dataset.portType = 'output';
        nodeEl.appendChild(outputPort);
    }

    // 設置拖拉功能
    makeDraggable(nodeEl);

    // 設置點擊選擇
    nodeEl.addEventListener('click', (e) => {
        e.stopPropagation();
        selectItem(node, 'node');
    });

    canvas.appendChild(nodeEl);
}

// 獲取節點顯示文字
function getNodeDisplayText(node) {
    switch (node.type) {
        case 'device':
            return node.data.deviceId || '未設定裝置ID';
        case 'publish':
            return node.data.topic || '未設定主題';
        case 'subscribe':
            return node.data.topic || '未設定主題';
        case 'function':
            return node.data.name || '未設定函式名稱';
        default:
            return '';
    }
}

// 使節點可拖拉
function makeDraggable(nodeEl) {
    nodeEl.addEventListener('pointerdown', (e) => {
        // 如果點擊的是連接埠，不進行拖拉
        if (e.target.classList.contains('port')) {
            return;
        }

        const rect = nodeEl.getBoundingClientRect();
        const canvasRect = canvas.getBoundingClientRect();
        
        dragState.isDragging = true;
        dragState.dragElement = nodeEl;
        dragState.offsetX = e.clientX - rect.left;
        dragState.offsetY = e.clientY - rect.top;

        nodeEl.setPointerCapture(e.pointerId);
        nodeEl.style.cursor = 'grabbing';
        nodeEl.style.zIndex = '10';
    });

    nodeEl.addEventListener('pointermove', (e) => {
        if (!dragState.isDragging || dragState.dragElement !== nodeEl) return;

        const canvasRect = canvas.getBoundingClientRect();
        const newX = e.clientX - canvasRect.left - dragState.offsetX;
        const newY = e.clientY - canvasRect.top - dragState.offsetY;

        nodeEl.style.left = `${Math.max(0, newX)}px`;
        nodeEl.style.top = `${Math.max(0, newY)}px`;

        // 更新節點資料
        const nodeId = nodeEl.dataset.id;
        const node = flow.nodes.find(n => n.id === nodeId);
        if (node) {
            node.x = newX;
            node.y = newY;
        }

        // 更新相關連線
        updateNodeConnections(nodeId);
    });

    nodeEl.addEventListener('pointerup', (e) => {
        if (dragState.dragElement === nodeEl) {
            dragState.isDragging = false;
            dragState.dragElement = null;
            nodeEl.style.cursor = 'move';
            nodeEl.style.zIndex = '2';
            nodeEl.releasePointerCapture(e.pointerId);
        }
    });
}

// 設置連線事件
function setupConnectionEvents() {
    canvas.addEventListener('pointerdown', (e) => {
        if (e.target.classList.contains('port') && e.target.classList.contains('output')) {
            startConnection(e);
        }
    });

    canvas.addEventListener('pointermove', (e) => {
        if (connectionState.isConnecting) {
            updateTempConnection(e);
        }
    });

    canvas.addEventListener('pointerup', (e) => {
        if (connectionState.isConnecting) {
            finishConnection(e);
        }
    });

    // 連線點擊事件
    connectionLayer.addEventListener('click', (e) => {
        if (e.target.classList.contains('connection') && !e.target.classList.contains('temp')) {
            const edgeId = e.target.dataset.id;
            const edge = flow.edges.find(edge => edge.id === edgeId);
            if (edge) {
                selectItem(edge, 'edge');
            }
        }
    });
}

// 開始連線
function startConnection(e) {
    const port = e.target;
    const nodeId = port.dataset.nodeId;
    
    connectionState.isConnecting = true;
    connectionState.sourceNode = nodeId;
    connectionState.sourcePort = port;

    // 創建臨時連線
    const tempLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    tempLine.classList.add('connection', 'temp');
    
    const portRect = port.getBoundingClientRect();
    const canvasRect = canvas.getBoundingClientRect();
    const startX = portRect.left + portRect.width / 2 - canvasRect.left;
    const startY = portRect.top + portRect.height / 2 - canvasRect.top;
    
    tempLine.setAttribute('x1', startX);
    tempLine.setAttribute('y1', startY);
    tempLine.setAttribute('x2', startX);
    tempLine.setAttribute('y2', startY);
    
    connectionLayer.appendChild(tempLine);
    connectionState.tempLine = tempLine;

    e.preventDefault();
    e.stopPropagation();
}

// 更新臨時連線
function updateTempConnection(e) {
    if (!connectionState.tempLine) return;

    const canvasRect = canvas.getBoundingClientRect();
    const endX = e.clientX - canvasRect.left;
    const endY = e.clientY - canvasRect.top;

    connectionState.tempLine.setAttribute('x2', endX);
    connectionState.tempLine.setAttribute('y2', endY);
}

// 完成連線
function finishConnection(e) {
    if (!connectionState.isConnecting) return;

    const targetPort = e.target;
    
    // 檢查是否連接到有效的輸入埠
    if (targetPort.classList.contains('port') && 
        targetPort.classList.contains('input') &&
        targetPort.dataset.nodeId !== connectionState.sourceNode) {
        
        // 創建連線
        const edgeId = genId();
        const edge = {
            id: edgeId,
            sourceId: connectionState.sourceNode,
            targetId: targetPort.dataset.nodeId,
            action: 'trigger',
            mode: 'async'
        };

        flow.edges.push(edge);
        renderConnection(edge);
        log(`已創建連線: ${edge.sourceId} → ${edge.targetId}`, 'info');
    }

    // 清理臨時連線
    if (connectionState.tempLine) {
        connectionState.tempLine.remove();
    }

    // 重置連線狀態
    connectionState.isConnecting = false;
    connectionState.sourceNode = null;
    connectionState.sourcePort = null;
    connectionState.tempLine = null;
}

// 渲染連線
function renderConnection(edge) {
    const sourceNode = flow.nodes.find(n => n.id === edge.sourceId);
    const targetNode = flow.nodes.find(n => n.id === edge.targetId);
    
    if (!sourceNode || !targetNode) return;

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.classList.add('connection');
    line.dataset.id = edge.id;
    line.setAttribute('marker-end', 'url(#arrowhead)');

    updateConnectionPosition(line, edge);
    connectionLayer.appendChild(line);
}

// 更新連線位置
function updateConnectionPosition(line, edge) {
    const sourceNode = flow.nodes.find(n => n.id === edge.sourceId);
    const targetNode = flow.nodes.find(n => n.id === edge.targetId);
    
    if (!sourceNode || !targetNode) return;

    const sourceX = sourceNode.x + 150; // 節點寬度 + 輸出埠位置
    const sourceY = sourceNode.y + 30;  // 節點高度的一半
    const targetX = targetNode.x;       // 輸入埠位置
    const targetY = targetNode.y + 30;

    line.setAttribute('x1', sourceX);
    line.setAttribute('y1', sourceY);
    line.setAttribute('x2', targetX);
    line.setAttribute('y2', targetY);
}

// 更新節點相關連線
function updateNodeConnections(nodeId) {
    flow.edges.forEach(edge => {
        if (edge.sourceId === nodeId || edge.targetId === nodeId) {
            const line = connectionLayer.querySelector(`[data-id="${edge.id}"]`);
            if (line) {
                updateConnectionPosition(line, edge);
            }
        }
    });
}

// 選擇項目
function selectItem(item, type) {
    clearSelection();
    selectedItem = { item, type };
    
    if (type === 'node') {
        const nodeEl = canvas.querySelector(`[data-id="${item.id}"]`);
        if (nodeEl) {
            nodeEl.classList.add('selected');
        }
        showNodeInspector(item);
    } else if (type === 'edge') {
        const lineEl = connectionLayer.querySelector(`[data-id="${item.id}"]`);
        if (lineEl) {
            lineEl.classList.add('selected');
        }
        showEdgeInspector(item);
    }
}

// 清除選擇
function clearSelection() {
    document.querySelectorAll('.selected').forEach(el => {
        el.classList.remove('selected');
    });
    selectedItem = null;
    showDefaultInspector();
}

// 顯示節點屬性檢視器
function showNodeInspector(node) {
    inspector.innerHTML = '';
    
    const title = document.createElement('h4');
    title.textContent = `${getNodeTypeName(node.type)} 屬性`;
    title.style.marginBottom = '15px';
    inspector.appendChild(title);

    switch (node.type) {
        case 'device':
            showDeviceInspector(node);
            break;
        case 'publish':
            showPublishInspector(node);
            break;
        case 'subscribe':
            showSubscribeInspector(node);
            break;
        case 'function':
            showFunctionInspector(node);
            break;
    }

    // 刪除按鈕
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'btn danger';
    deleteBtn.textContent = '🗑️ 刪除節點';
    deleteBtn.onclick = () => deleteNode(node.id);
    inspector.appendChild(deleteBtn);
}

// 顯示裝置屬性檢視器
function showDeviceInspector(node) {
    const form = document.createElement('form');
    form.innerHTML = `
        <div class="form-group">
            <label>裝置 ID:</label>
            <input type="text" name="deviceId" value="${node.data.deviceId || ''}" placeholder="例如: sensor01">
        </div>
        <div class="form-group">
            <label>MQTT Broker URL:</label>
            <input type="text" name="brokerUrl" value="${node.data.brokerUrl || 'wss://mqtt-edu.webduino.io/mqtt'}">
        </div>
        <div class="form-group">
            <label>使用者名稱:</label>
            <input type="text" name="username" value="${node.data.username || 'hsh2025'}">
        </div>
        <div class="form-group">
            <label>密碼:</label>
            <input type="password" name="password" value="${node.data.password || 'hsh2025'}">
        </div>
    `;

    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'btn';
    saveBtn.textContent = '💾 儲存變更';
    saveBtn.onclick = () => {
        const formData = new FormData(form);
        node.data.deviceId = formData.get('deviceId');
        node.data.brokerUrl = formData.get('brokerUrl');
        node.data.username = formData.get('username');
        node.data.password = formData.get('password');
        
        updateNodeDisplay(node);
        log(`已更新裝置設定: ${node.data.deviceId}`, 'info');
    };

    form.appendChild(saveBtn);
    inspector.appendChild(form);
}

// 顯示發布節點屬性檢視器
function showPublishInspector(node) {
    const form = document.createElement('form');
    form.innerHTML = `
        <div class="form-group">
            <label>主題 (目標.動作):</label>
            <input type="text" name="topic" value="${node.data.topic || ''}" placeholder="例如: device01.turnOn">
        </div>
        <div class="form-group">
            <label>負載 (JSON):</label>
            <textarea name="payload" rows="4" placeholder='{"value": 1}'>${node.data.payload || '{}'}</textarea>
        </div>
        <div class="form-group">
            <label>QoS 等級:</label>
            <select name="qos">
                <option value="0" ${node.data.qos === 0 ? 'selected' : ''}>0 - 最多一次</option>
                <option value="1" ${node.data.qos === 1 ? 'selected' : ''}>1 - 至少一次</option>
                <option value="2" ${node.data.qos === 2 ? 'selected' : ''}>2 - 只有一次</option>
            </select>
        </div>
        <div class="form-group">
            <label>模式:</label>
            <select name="mode">
                <option value="async" ${node.data.mode === 'async' ? 'selected' : ''}>非同步</option>
                <option value="sync" ${node.data.mode === 'sync' ? 'selected' : ''}>同步</option>
            </select>
        </div>
    `;

    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'btn';
    saveBtn.textContent = '💾 儲存變更';
    saveBtn.onclick = () => {
        const formData = new FormData(form);
        node.data.topic = formData.get('topic');
        node.data.payload = formData.get('payload');
        node.data.qos = parseInt(formData.get('qos'));
        node.data.mode = formData.get('mode');
        
        updateNodeDisplay(node);
        log(`已更新發布節點設定: ${node.data.topic}`, 'info');
    };

    form.appendChild(saveBtn);
    inspector.appendChild(form);
}

// 顯示訂閱節點屬性檢視器
function showSubscribeInspector(node) {
    const form = document.createElement('form');
    form.innerHTML = `
        <div class="form-group">
            <label>主題:</label>
            <input type="text" name="topic" value="${node.data.topic || ''}" placeholder="例如: sensor/+/data">
        </div>
        <div class="form-group">
            <label>處理函式:</label>
            <textarea name="handler" rows="6">${node.data.handler || 'function(message) {\n  console.log(message);\n}'}</textarea>
        </div>
    `;

    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'btn';
    saveBtn.textContent = '💾 儲存變更';
    saveBtn.onclick = () => {
        const formData = new FormData(form);
        node.data.topic = formData.get('topic');
        node.data.handler = formData.get('handler');
        
        updateNodeDisplay(node);
        log(`已更新訂閱節點設定: ${node.data.topic}`, 'info');
    };

    form.appendChild(saveBtn);
    inspector.appendChild(form);
}

// 顯示函式節點屬性檢視器
function showFunctionInspector(node) {
    const form = document.createElement('form');
    form.innerHTML = `
        <div class="form-group">
            <label>函式名稱:</label>
            <input type="text" name="name" value="${node.data.name || ''}" placeholder="例如: dataProcessor">
        </div>
        <div class="form-group">
            <label>函式程式碼:</label>
            <textarea name="code" rows="8">${node.data.code || 'function process(input) {\n  return input;\n}'}</textarea>
        </div>
    `;

    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'btn';
    saveBtn.textContent = '💾 儲存變更';
    saveBtn.onclick = () => {
        const formData = new FormData(form);
        node.data.name = formData.get('name');
        node.data.code = formData.get('code');
        
        updateNodeDisplay(node);
        log(`已更新函式節點設定: ${node.data.name}`, 'info');
    };

    form.appendChild(saveBtn);
    inspector.appendChild(form);
}

// 顯示連線屬性檢視器
function showEdgeInspector(edge) {
    inspector.innerHTML = '';
    
    const title = document.createElement('h4');
    title.textContent = '連線屬性';
    title.style.marginBottom = '15px';
    inspector.appendChild(title);

    const form = document.createElement('form');
    form.innerHTML = `
        <div class="form-group">
            <label>來源節點:</label>
            <input type="text" value="${edge.sourceId}" readonly>
        </div>
        <div class="form-group">
            <label>目標節點:</label>
            <input type="text" value="${edge.targetId}" readonly>
        </div>
        <div class="form-group">
            <label>動作:</label>
            <input type="text" name="action" value="${edge.action || 'trigger'}" placeholder="例如: trigger, process">
        </div>
        <div class="form-group">
            <label>模式:</label>
            <select name="mode">
                <option value="async" ${edge.mode === 'async' ? 'selected' : ''}>非同步</option>
                <option value="sync" ${edge.mode === 'sync' ? 'selected' : ''}>同步</option>
            </select>
        </div>
    `;

    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'btn';
    saveBtn.textContent = '💾 儲存變更';
    saveBtn.onclick = () => {
        const formData = new FormData(form);
        edge.action = formData.get('action');
        edge.mode = formData.get('mode');
        log(`已更新連線設定: ${edge.sourceId} → ${edge.targetId}`, 'info');
    };

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'btn danger';
    deleteBtn.textContent = '🗑️ 刪除連線';
    deleteBtn.onclick = () => deleteEdge(edge.id);

    form.appendChild(saveBtn);
    form.appendChild(deleteBtn);
    inspector.appendChild(form);
}

// 顯示預設檢視器
function showDefaultInspector() {
    inspector.innerHTML = `
        <p style="color: #999; text-align: center; margin-top: 50px;">
            選擇一個節點或連線來編輯屬性
        </p>
    `;
}

// 更新節點顯示
function updateNodeDisplay(node) {
    const nodeEl = canvas.querySelector(`[data-id="${node.id}"]`);
    if (nodeEl) {
        const content = nodeEl.querySelector('.node-content');
        if (content) {
            content.textContent = getNodeDisplayText(node);
        }
    }
}

// 刪除節點
function deleteNode(nodeId) {
    // 刪除相關連線
    const relatedEdges = flow.edges.filter(edge => 
        edge.sourceId === nodeId || edge.targetId === nodeId
    );
    relatedEdges.forEach(edge => deleteEdge(edge.id));

    // 刪除節點
    flow.nodes = flow.nodes.filter(node => node.id !== nodeId);
    
    const nodeEl = canvas.querySelector(`[data-id="${nodeId}"]`);
    if (nodeEl) {
        nodeEl.remove();
    }

    clearSelection();
    log(`已刪除節點: ${nodeId}`, 'warn');
}

// 刪除連線
function deleteEdge(edgeId) {
    flow.edges = flow.edges.filter(edge => edge.id !== edgeId);
    
    const lineEl = connectionLayer.querySelector(`[data-id="${edgeId}"]`);
    if (lineEl) {
        lineEl.remove();
    }

    clearSelection();
    log(`已刪除連線: ${edgeId}`, 'warn');
}

// 執行流程
async function runFlow() {
    if (isRunning) return;

    try {
        isRunning = true;
        document.getElementById('run-btn').disabled = true;
        log('開始執行 IoT 流程...', 'info');

        // 初始化所有裝置節點
        const deviceNodes = flow.nodes.filter(node => node.type === 'device');
        
        for (const node of deviceNodes) {
            if (!node.data.deviceId) {
                log(`裝置節點 ${node.id} 缺少裝置ID`, 'error');
                continue;
            }

            const device = new IoTDevice(node.data.deviceId);
            device.brokerUrl = node.data.brokerUrl || 'wss://mqtt-edu.webduino.io/mqtt';
            device.username = node.data.username || 'hsh2025';
            device.password = node.data.password || 'hsh2025';

            try {
                await device.connect();
                devices.set(node.data.deviceId, device);
                log(`裝置 ${node.data.deviceId} 已連線`, 'info');

                // 設置訂閱處理器
                setupDeviceHandlers(device, node);
            } catch (error) {
                log(`裝置 ${node.data.deviceId} 連線失敗: ${error.message}`, 'error');
            }
        }

        // 設置訂閱節點
        setupSubscribeNodes();

        log('IoT 流程執行中...', 'info');

    } catch (error) {
        log(`執行流程時發生錯誤: ${error.message}`, 'error');
        isRunning = false;
        document.getElementById('run-btn').disabled = false;
    }
}

// 設置裝置處理器
function setupDeviceHandlers(device, deviceNode) {
    // 找到所有連接到此裝置的邊
    const incomingEdges = flow.edges.filter(edge => edge.targetId === deviceNode.id);
    
    incomingEdges.forEach(edge => {
        const sourceNode = flow.nodes.find(n => n.id === edge.sourceId);
        if (sourceNode && sourceNode.type === 'function') {
            // 為函式節點設置處理器
            device.proc(edge.action, async (message) => {
                try {
                    // 執行函式節點的程式碼
                    const func = new Function('input', sourceNode.data.code + '\nreturn process(input);');
                    const result = func(message.payload);
                    log(`函式 ${sourceNode.data.name} 處理完成`, 'info');
                    return result;
                } catch (error) {
                    log(`函式 ${sourceNode.data.name} 執行錯誤: ${error.message}`, 'error');
                    throw error;
                }
            });
        }
    });
}

// 設置訂閱節點
function setupSubscribeNodes() {
    const subscribeNodes = flow.nodes.filter(node => node.type === 'subscribe');
    
    subscribeNodes.forEach(node => {
        if (!node.data.topic) return;

        // 找一個裝置來訂閱（簡化處理）
        const device = devices.values().next().value;
        if (device) {
            try {
                const handler = new Function('message', node.data.handler);
                device.client.subscribe(node.data.topic, (err) => {
                    if (!err) {
                        log(`已訂閱主題: ${node.data.topic}`, 'info');
                    } else {
                        log(`訂閱主題失敗: ${node.data.topic}`, 'error');
                    }
                });

                // 覆蓋預設訊息處理器以包含訂閱處理
                const originalHandler = device.handleMessage.bind(device);
                device.handleMessage = async (topic, message) => {
                    // 首先執行原始處理器
                    await originalHandler(topic, message);
                    
                    // 然後檢查訂閱節點
                    if (topic.match(new RegExp(node.data.topic.replace(/\+/g, '[^/]+').replace(/#/g, '.*')))) {
                        try {
                            handler({ topic, payload: JSON.parse(message.toString()) });
                        } catch (error) {
                            log(`訂閱處理器錯誤: ${error.message}`, 'error');
                        }
                    }
                };
            } catch (error) {
                log(`設置訂閱節點錯誤: ${error.message}`, 'error');
            }
        }
    });
}

// 停止流程
async function stopFlow() {
    if (!isRunning) return;

    try {
        log('正在停止 IoT 流程...', 'warn');

        // 斷開所有裝置連線
        for (const [deviceId, device] of devices) {
            try {
                await device.disconnect();
                log(`裝置 ${deviceId} 已斷線`, 'info');
            } catch (error) {
                log(`裝置 ${deviceId} 斷線失敗: ${error.message}`, 'error');
            }
        }

        devices.clear();
        isRunning = false;
        document.getElementById('run-btn').disabled = false;
        log('IoT 流程已停止', 'info');

    } catch (error) {
        log(`停止流程時發生錯誤: ${error.message}`, 'error');
    }
}

// 清空流程
function clearFlow() {
    if (isRunning) {
        alert('請先停止執行中的流程');
        return;
    }

    if (confirm('確定要清空所有節點和連線嗎？此操作無法復原。')) {
        flow.nodes = [];
        flow.edges = [];
        canvas.innerHTML = '';
        connectionLayer.innerHTML = `
            <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="7" 
                        refX="9" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="#666" />
                </marker>
            </defs>
        `;
        clearSelection();
        log('已清空所有節點和連線', 'warn');
    }
}

// 儲存流程
function saveFlow() {
    const flowData = {
        nodes: flow.nodes,
        edges: flow.edges,
        timestamp: new Date().toISOString()
    };

    const dataStr = JSON.stringify(flowData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = `iot-flow-${Date.now()}.json`;
    link.click();

    log('流程已匯出', 'info');
}

// 載入流程
function loadFlow() {
    if (isRunning) {
        alert('請先停止執行中的流程');
        return;
    }

    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const flowData = JSON.parse(e.target.result);
                
                // 清空現有流程
                clearFlow();
                
                // 載入節點
                if (flowData.nodes) {
                    flow.nodes = flowData.nodes;
                    flow.nodes.forEach(node => renderNode(node));
                }
                
                // 載入連線
                if (flowData.edges) {
                    flow.edges = flowData.edges;
                    flow.edges.forEach(edge => renderConnection(edge));
                }

                // 更新 ID 計數器
                const maxId = Math.max(
                    ...flow.nodes.map(n => parseInt(n.id.substring(1))),
                    ...flow.edges.map(e => parseInt(e.id.substring(1))),
                    0
                );
                nextId = maxId + 1;

                log('流程已載入', 'info');
            } catch (error) {
                log(`載入流程失敗: ${error.message}`, 'error');
            }
        };
        reader.readAsText(file);
    };
    input.click();
}

// 切換日誌面板
function toggleLog() {
    logPanel.classList.toggle('visible');
}

// 記錄日誌
function log(message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;
    logEntry.textContent = `[${timestamp}] ${message}`;
    
    logContent.appendChild(logEntry);
    logContent.scrollTop = logContent.scrollHeight;

    // 限制日誌條目數量
    const entries = logContent.querySelectorAll('.log-entry');
    if (entries.length > 100) {
        entries[0].remove();
    }
}

// 演示功能
function createBasicDemo() {
    if (isRunning) {
        alert('請先停止執行中的流程');
        return;
    }

    // 清空現有內容
    clearFlow();

    // 創建演示節點
    const sensorDevice = {
        id: genId(),
        type: 'device',
        x: 100,
        y: 150,
        data: {
            deviceId: 'sensor01',
            brokerUrl: 'wss://mqtt-edu.webduino.io/mqtt',
            username: 'hsh2025',
            password: 'hsh2025',
            handlers: []
        }
    };

    const processorFunction = {
        id: genId(),
        type: 'function',
        x: 350,
        y: 150,
        data: {
            name: 'dataProcessor',
            code: `function process(input) {
  const data = input.payload || input;
  return {
    processedAt: new Date().toISOString(),
    temperature: data.temperature * 1.8 + 32, // 轉換為華氏溫度
    humidity: data.humidity,
    status: data.temperature > 25 ? 'HOT' : 'NORMAL'
  };
}`
        }
    };

    const controllerDevice = {
        id: genId(),
        type: 'device',
        x: 600,
        y: 150,
        data: {
            deviceId: 'controller01',
            brokerUrl: 'wss://mqtt-edu.webduino.io/mqtt',
            username: 'hsh2025',
            password: 'hsh2025',
            handlers: []
        }
    };

    // 添加節點到流程
    flow.nodes.push(sensorDevice, processorFunction, controllerDevice);

    // 創建連線
    const edge1 = {
        id: genId(),
        sourceId: sensorDevice.id,
        targetId: processorFunction.id,
        action: 'process',
        mode: 'async'
    };

    const edge2 = {
        id: genId(),
        sourceId: processorFunction.id,
        targetId: controllerDevice.id,
        action: 'control',
        mode: 'async'
    };

    flow.edges.push(edge1, edge2);

    // 渲染所有元素
    flow.nodes.forEach(node => renderNode(node));
    flow.edges.forEach(edge => renderConnection(edge));

    log('已創建基本演示範例', 'info');
}

function createSensorDemo() {
    if (isRunning) {
        alert('請先停止執行中的流程');
        return;
    }

    // 清空現有內容
    clearFlow();

    // 創建感測器監控演示
    const tempSensor = {
        id: genId(),
        type: 'device',
        x: 80,
        y: 100,
        data: {
            deviceId: 'tempSensor',
            brokerUrl: 'wss://mqtt-edu.webduino.io/mqtt',
            username: 'hsh2025',
            password: 'hsh2025',
            handlers: []
        }
    };

    const humiditySensor = {
        id: genId(),
        type: 'device',
        x: 80,
        y: 250,
        data: {
            deviceId: 'humiditySensor',
            brokerUrl: 'wss://mqtt-edu.webduino.io/mqtt',
            username: 'hsh2025',
            password: 'hsh2025',
            handlers: []
        }
    };

    const dataAggregator = {
        id: genId(),
        type: 'function',
        x: 350,
        y: 175,
        data: {
            name: 'dataAggregator',
            code: `function process(input) {
  // 聚合感測器資料
  const timestamp = new Date().toISOString();
  return {
    timestamp: timestamp,
    sensorData: input.payload || input,
    aggregatedBy: 'dataAggregator',
    alert: input.payload?.value > 30 ? 'HIGH_VALUE_ALERT' : 'NORMAL'
  };
}`
        }
    };

    const logSubscriber = {
        id: genId(),
        type: 'subscribe',
        x: 600,
        y: 100,
        data: {
            topic: 'sensors/+/data',
            handler: `function(message) {
  console.log('📊 感測器資料:', message);
  // 這裡可以添加資料視覺化邏輯
}`
        }
    };

    const alertSystem = {
        id: genId(),
        type: 'device',
        x: 600,
        y: 250,
        data: {
            deviceId: 'alertSystem',
            brokerUrl: 'wss://mqtt-edu.webduino.io/mqtt',
            username: 'hsh2025',
            password: 'hsh2025',
            handlers: []
        }
    };

    // 添加節點到流程
    flow.nodes.push(tempSensor, humiditySensor, dataAggregator, logSubscriber, alertSystem);

    // 創建連線
    const connections = [
        {
            id: genId(),
            sourceId: tempSensor.id,
            targetId: dataAggregator.id,
            action: 'aggregate',
            mode: 'async'
        },
        {
            id: genId(),
            sourceId: humiditySensor.id,
            targetId: dataAggregator.id,
            action: 'aggregate',
            mode: 'async'
        },
        {
            id: genId(),
            sourceId: dataAggregator.id,
            targetId: alertSystem.id,
            action: 'alert',
            mode: 'async'
        }
    ];

    flow.edges.push(...connections);

    // 渲染所有元素
    flow.nodes.forEach(node => renderNode(node));
    flow.edges.forEach(edge => renderConnection(edge));

    log('已創建感測器監控演示範例', 'info');
} 