import espnow, ubinascii, network
import machine, time, gc

class ESPNow:

    def __init__(self, retry=0, timeout=50, set_channel=-1, hub=''):
        # 定義ESPNow通訊指令碼
        ESPNow.CMD_RST = b'\xff\xff'           # 重置指令
        ESPNow.CMD_ACK = b'\xff\xfe'           # 確認回應指令
        ESPNow.CMD_BOOT = b'\xff\x00'          # 開機指令
        ESPNow.CMD_JOIN = b'\xff\x13'          # 加入節點指令
        ESPNow.CMD_CHANNEL = b'\xff\x14'       # 設定頻道指令
        ESPNow.CMD_STOP = b'\xf4\xfe'          # 停止指令
        ESPNow.CMD_FILE = b'\xf4\x10'          # 傳輸文件指令
        ESPNow.CMD_DONE = b'\xf4\x11'          # 文件傳輸完成指令
        ESPNow.CMD_FILE_WRITE_ACK = b'\xf4\x12' # 文件寫入確認回應

        # 初始化 Wi-Fi 連接並啟動 ESPNow
        self.wifi_reset()
        self.e = espnow.ESPNow()  # 創建 ESPNow 對象
        self.e.active(True)  # 啟動 ESPNow
        self.peer_mac = network.WLAN().config('mac')  # 取得本機的 MAC 位址
        self.peer_mac_str = (ubinascii.hexlify(self.peer_mac, ':').decode())  # 將 MAC 位址轉換為字串格式
        print("[MAC] " + self.peer_mac_str)  # 輸出本機 MAC 位址
        #self.e.add_peer(self.peer_mac)  # 將本機的 MAC 加入為節點
        self.nodeMap = {}  # 存儲已加入的節點
        self.file_buffer = {}  # 用來存儲接收到的文件數據
        self.callback = None  # 用於接收消息的回調函數
        self.hub = hub  # 存儲hub參數
        self.ack_channel(retry, timeout, set_channel)  # 確認通訊頻道

    # 根據 retry 參數嘗試確認頻道
    def ack_channel(self, retry, timeout=500, set_channel=-1):
        # 如果設定了hub，直接連接到指定的hub
        if self.hub:
            # 檢查是否是默認頻道，如果是則掃描尋找指定hub
            if set_channel == -1:
                print(f"掃描尋找指定的hub: {self.hub}")
                self.scan_for_hub(self.hub, timeout)
            else:
                print(f"直接連接到hub: {self.hub}，使用頻道: {set_channel}")
                self.set_channel(set_channel)  # 設置頻道
                self.join(self.hub)  # 直接加入hub
            return
            
        if retry == 0:
            self.set_channel(set_channel)  # 設置為頻道1
            self.broadcast_mac()  # 廣播當前的 MAC 位址
            self.internal_recv_callback(self.e)  # 使用 500ms 超時接收訊息
        elif retry == -1:
            while not self.broadcast_all_channel(timeout): pass  # 若設定為 -1，則無限嘗試直到成功
        else:
            for i in range(retry):
                if self.broadcast_all_channel(timeout):  # 根據設定的次數重試
                    break

    # 掃描所有頻道，尋找指定的hub
    def scan_for_hub(self, target_hub, timeout=500):
        target_bytes = None
        # 將目標hub的字符串轉換為bytes
        if ':' in target_hub:
            data = target_hub.split(':')
            target_bytes = bytes([int(part, 16) for part in data])
        else:
            target_bytes = target_hub
            
        target_str = ':'.join(f'{byte:02x}' for byte in target_bytes) if isinstance(target_bytes, bytes) else target_hub
        
        found = False
        attempt = 0
        
        while not found:
            attempt += 1
            print(f"掃描嘗試 #{attempt} 尋找 hub: {target_str}")
            
            for i in range(1, 12):  # ESP32 支援的 Wi-Fi 頻道範圍是 1 到 11
                print(f"scan:{i} , timeout:{timeout}")
                self.set_channel(i)  # 設定當前的 Wi-Fi 頻道
                self.broadcast_mac()  # 廣播當前的 MAC 位址
                gc.collect()  # 進行垃圾回收
                
                peer, msg = self.internal_recv_callback(self.e, timeout)  # 使用超時接收來自其他節點的消息
                
                if peer is not None:  # 如果成功接收到消息
                    peer_str = (ubinascii.hexlify(peer, ':').decode())  # 轉換接收到的 MAC 為字串格式
                    print(f"收到來自 {peer_str} 的回應")
                    
                    # 檢查是否是目標hub
                    if peer_str == target_str:
                        print(f"找到目標 hub: {target_str}，頻道: {i}")
                        self.join(target_hub)  # 加入找到的hub
                        found = True
                        break
            
            if not found:
                print(f"未找到目標 hub: {target_str}，將再次嘗試掃描")
                time.sleep(1)  # 短暫延遲後再試

    # 掃描所有頻道，並廣播當前節點的 MAC 位址
    def broadcast_all_channel(self,timeout=500):
        for i in range(1, 12):  # ESP32 支援的 Wi-Fi 頻道範圍是 1 到 11
            print(f"scan:{i} , timeout:{timeout}")
            self.set_channel(i)  # 設定當前的 Wi-Fi 頻道
            self.broadcast_mac()  # 廣播當前的 MAC 位址
            gc.collect()  # 進行垃圾回收
            peer, msg = self.internal_recv_callback(self.e, timeout)  # 使用 500ms 超時接收來自其他節點的消息
            if peer is not None:  # 如果成功接收到消息
                peer_str = (ubinascii.hexlify(peer, ':').decode())  # 轉換接收到的 MAC 為字串格式
                print(f"connect to {peer_str} , set channel:{i}")
                return True
        return False

    # 返回當前 AP 的 Wi-Fi 頻道
    def channel(self):
        return self.ap.config('channel')

    # 設置 Wi-Fi 頻道
    def set_channel(self, channel):
        self.sta.active(False)
        self.ap.active(False)
        self.sta.active(True)
        while not self.sta.active(): 
            time.sleep(0.1)
        self.ap.active(True)
        time.sleep(0.1)
        self.ap.config(channel=channel)  # 設置 AP 的 Wi-Fi 頻道

    # 重置 Wi-Fi 狀態並啟動 STA 和 AP 模式
    def wifi_reset(self):
        self.sta = network.WLAN(network.STA_IF)  # STA 模式（客戶端模式）
        self.ap = network.WLAN(network.AP_IF)  # AP 模式（訪問點模式）
        self.sta.active(False)
        self.ap.active(False)
        self.sta.active(True)  # 啟動 STA 模式
        while not self.sta.active(): 
            time.sleep(0.1)
        self.ap.active(True)  # 啟動 AP 模式

    # 根據接收到的指令碼返回對應的指令名稱
    def cmd(self, msg):
        if msg == ESPNow.CMD_STOP:
            return "STOP"
        elif msg == ESPNow.CMD_RST:
            return "RST"
        elif msg == ESPNow.CMD_BOOT:
            return "BOOT"
        elif msg == ESPNow.CMD_JOIN:
            return "JOIN"
        elif msg[0:2] == ESPNow.CMD_CHANNEL:
            return "CHANNEL"
        elif msg[0:2] == ESPNow.CMD_FILE:
            return "FILE"
        elif msg[0:2] == ESPNow.CMD_FILE_WRITE_ACK:
            return "CMD_FILE_WRITE_ACK"
        elif msg == ESPNow.CMD_ACK:
            return "ACK"
        elif msg == ESPNow.CMD_DONE:
            return "DONE"
        return f"UNKNOWN: {msg}"

    # 將 peer_data 加入到節點列表中
    def join(self, peer_data):
        peer = ''
        if isinstance(peer_data, bytes):
            peer = peer_data
        else:
            data = peer_data.split(':')
            peer = bytes([int(part, 16) for part in data])

        try:  # 嘗試將 peer 加入到節點，可能已經加入過
            peer_str = ':'.join(f'{byte:02x}' for byte in peer)
            self.nodeMap[peer_str] = peer
            print(f"add peer: {peer_str}")
            self.e.add_peer(peer)
        except Exception as e:
            pass

    # 發送指令給指定的節點
    def sendCmd(self, cmd, peer_mac_str):
        print(f"-> [{peer_mac_str}] cmd:{self.cmd(cmd)}")
        if peer_mac_str in self.nodeMap:
            data = peer_mac_str.split(':')
            peer = bytes([int(part, 16) for part in data])
            self.e.send(peer, cmd)

    # 發送加入節點的指令
    def sendJoin(self, to_peer_mac_str, data_peer_str):
        if to_peer_mac_str in self.nodeMap:
            message = bytearray(ESPNow.CMD_JOIN)
            message.extend(data_peer_str)
            self.e.send(self.nodeMap[to_peer_mac_str], message)

    # 發送消息給所有已加入的節點
    def send(self, peer_mac, message):
        print(f"send {peer_mac}")
        self.e.send(self.nodeMap[peer_mac], message)

    # 發送消息給所有已加入的節點
    def sendAll(self, message, timeout=0):
        for peer_mac in self.nodeMap.keys():
            print(f"send {peer_mac}")
            self.e.send(self.nodeMap[peer_mac], message)
        
        # 如果設定了超時，則等待 ACK 回應
        if timeout > 0:
            peer, msg = self.internal_recv_callback(self.e, 100)  # 使用較短的超時檢查
            # 判斷 msg 前兩個字節是否為 ESPNow.CMD_ACK
            if peer is not None and msg[0:2] == ESPNow.CMD_ACK:
                print(f"sendAll {message} , ack:{True}")
                return True  # 收到 ACK 回應，返回 True
            else:
                return False  # 超時未收到 ACK，返回 False
        return None  # 如果沒有設定超時，則不返回結果

    # 廣播消息給所有節點
    def broadcast(self, message):
        self.e.send(b'\xff\xff\xff\xff\xff\xff', message)

    # 廣播當前節點的 MAC 位址
    def broadcast_mac(self):
        print(f"-> [ff:ff:ff:ff:ff:ff] cmd: {self.cmd(ESPNow.CMD_BOOT)}")
        
        # 檢查是否已經存在廣播節點
        try:
            self.e.add_peer(b'\xff\xff\xff\xff\xff\xff')
        except OSError:
            # 忽略錯誤，可能是節點已存在
            pass
        # 發送廣播消息
        self.e.send(b'\xff\xff\xff\xff\xff\xff', ESPNow.CMD_BOOT)
        time.sleep(0.5)
        # 廣播完畢後，移除該廣播節點
        #self.e.del_peer(b'\xff\xff\xff\xff\xff\xff')

    def recv(self, userCallback):
        def callback(*args):
            peer,msg = self.internal_recv_callback(args[0], 0)  # 使用默認超時 0（永不超時）
            if peer is not None:
                userCallback(peer,msg,self.e.peers_table)
        self.e.irq(callback)


    def internal_recv_callback(self,espObj, timeout=0):
        # 輔助函數，尋找 bytearray 中的特定子數組
        def bytearray_find(haystack, needle, start=0):
            needle_len = len(needle)
            for i in range(start, len(haystack) - needle_len + 1):
                if haystack[i:i + needle_len] == needle:
                    return i
            return -1
        #print(f"incoming... timeout:{timeout}")
        peer, msg = espObj.recv(timeout)
        if peer is not None:
            peer_str = ':'.join(f'{byte:02x}' for byte in peer)
            #print(f"Received from {peer_str}, msg: {msg}")
            
            # 處理收到的命令
            if len(msg) == 2:
                print(f"<- [{peer_str}] cmd: {self.cmd(msg)}")
                if msg == ESPNow.CMD_RST:
                    machine.reset()  # 如果收到重置命令，執行設備重啟
                if msg == ESPNow.CMD_ACK:
                    print("ACK")
                elif msg == ESPNow.CMD_STOP:
                    self.sendCmd(ESPNow.CMD_ACK, peer_str)  # 發送確認回應
                    while True:
                        espObj.recv(1000)  # 繼續阻塞接收
            elif len(msg) > 4 and msg[0:2] == ESPNow.CMD_JOIN:
                peer_str = msg[2:].decode()
                self.join(peer_str)  # 加入收到的 peer
            elif len(msg) > 4 and msg[0:2] == ESPNow.CMD_CHANNEL:
                channel_str = msg[2:].decode()
                self.set_channel(int(channel_str))  # 設置 Wi-Fi 頻道
            elif len(msg) > 4 and msg[0:2] == ESPNow.CMD_FILE:
                print(f"<- [{peer_str}] cmd: {self.cmd(msg)}")
                chunk_size = msg[2]
                total_length = int.from_bytes(msg[3:7], 'big')
                end_of_filename = bytearray_find(msg, b'\n', 7)
                filename = msg[7:end_of_filename].decode()
                start_byte = int.from_bytes(msg[end_of_filename + 1:end_of_filename + 3], 'big')
                file_data = msg[end_of_filename + 3:]
                if filename not in self.file_buffer:
                    self.file_buffer[filename] = bytearray(total_length)  # 初始化文件緩衝區
                self.file_buffer[filename][start_byte:start_byte + len(file_data)] = file_data  # 儲存文件塊
                if total_length == (start_byte + len(file_data)):  # 如果文件接收完成
                    with open(filename, 'wb') as f:
                        f.write(self.file_buffer[filename])  # 寫入文件
                    self.file_buffer = {}
                    gc.collect()
                    print("File " + filename + " written successfully")
                    self.sendCmd(ESPNow.CMD_FILE_WRITE_ACK, peer_str)  # 發送文件寫入確認
                    self.sendCmd(ESPNow.CMD_DONE, peer_str)  # 發送完成確認
                else:
                    self.sendCmd(ESPNow.CMD_FILE_WRITE_ACK, peer_str)  # 發送確認，文件未完全接收
            return peer, msg
        return None,None