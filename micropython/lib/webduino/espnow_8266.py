import espnow, ubinascii, network
import machine, time, gc

"""
2024/08/20 增加 sendJoin 功能，加入指定節點接收訊息
2024/08/28 增加廣播掃描確認channel頻道
2024/09/07 修改預設使用ch1進行廣播，但是可以設定retry決定嘗試次數: -1:永久嘗試 , 1~n:嘗試次數
2024/09/10 增加 time.sleep(0.1) 等候 self.ap.active(True)
2024/10/01 增加 send 方法
"""

class ESPNow:

    def __init__(self,retry=0):
        ESPNow.CMD_RST= b'\xff\xff'
        ESPNow.CMD_ACK= b'\xff\xfe'
        ESPNow.CMD_BOOT= b'\xff\x00'
        ESPNow.CMD_JOIN= b'\xff\x13'
        ESPNow.CMD_CHANNEL= b'\xff\x14'

        ESPNow.CMD_STOP = b'\xf4\xfe'
        ESPNow.CMD_FILE= b'\xf4\x10'
        ESPNow.CMD_DONE= b'\xf4\x11'
        ESPNow.CMD_FILE_WRITE_ACK= b'\xf4\x12'
        self.wifi_reset()
        self.e = espnow.ESPNow()
        self.e.active(True)
        self.peer_mac = network.WLAN().config('mac')
        self.peer_mac_str = (ubinascii.hexlify(self.peer_mac, ':').decode())
        self.e.add_peer(self.peer_mac)
        self.nodeMap = {}
        self.callback = None
        self.file_buffer = {}
        self.ack_channel(retry)
        print("[MAC] " + self.peer_mac_str)

    def ack_channel(self,retry):
        if(retry==0):
            self.set_channel(1)
            self.broadcast_mac()
            gc.collect()
            peer, msg = self.e.irecv(250)
        elif retry == -1:
            while not self.broadcast_all_channel(): pass
        else:
            for i in range(retry):
                if(self.broadcast_all_channel()): break

    def broadcast_all_channel(self):
        for i in range(1,15):
            print(f"scan:{i}")
            self.set_channel(i)
            self.broadcast_mac()
            gc.collect()
            peer, msg = self.e.irecv(250)
            if not peer==None:
                peer_str = (ubinascii.hexlify(peer, ':').decode())
                print(f"connect to {peer_str} , set channel:{i}")
                self.broadcast_mac()
                self.irecv(0.25)
                return True
        return False

    def channel(self):
        return self.ap.config('channel')
        
    def set_channel(self,channel):
        self.sta.active(False)
        self.ap.active(False)
        self.sta.active(True)
        while not self.sta.active(): time.sleep(0.1)
        self.ap.active(True)
        time.sleep(0.1)
        self.ap.config(channel=channel)

    def wifi_reset(self):
        self.sta = network.WLAN(network.STA_IF)
        self.ap = network.WLAN(network.AP_IF)
        self.sta.active(False)
        self.ap.active(False)
        self.sta.active(True)
        while not self.sta.active(): time.sleep(0.1)
        self.sta.disconnect()   # For ESP8266
        self.ap.active(True)

    def cmd(self,msg):
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
    
    def join(self,peer_data):
        peer = ''
        if isinstance(peer_data, bytes):
            peer = peer_data
        else:
            data = peer_data.split(':')
            peer = bytes([int(part, 16) for part in data])

        try: # maybe already join
            peer_str =':'.join(f'{byte:02x}' for byte in peer)
            self.nodeMap[peer_str] = peer
            print(f"add peer: {peer_str}")
            self.e.add_peer(peer)
        except Exception as e:
            pass#print(e)

    def sendCmd(self, cmd , peer_mac_str):
        print(f"-> [{peer_mac_str}] cmd:{self.cmd(cmd)}")
        if peer_mac_str in self.nodeMap:
            #print(f"send cmd: {cmd}")
            # 將 peer_data 分割成列表
            data = peer_mac_str.split(':')
            # 將每個十六進制字符串轉換為整數，然後組合成 bytes 對象
            peer = bytes([int(part, 16) for part in data])
            self.e.send(peer, cmd)

    def sendJoin(self,to_peer_mac_str, data_peer_str):
        if to_peer_mac_str in self.nodeMap:
            message = bytearray(ESPNow.CMD_JOIN)
            message.extend(data_peer_str)
            self.e.send(self.nodeMap[to_peer_mac_str], message )

    # 發送消息給所有已加入的節點
    def send(self, peer_mac, message):
        print(f"send {peer_mac}")
        if peer_mac in self.nodeMap:
            self.e.send(self.nodeMap[peer_mac], message)

    # 發送消息給所有已加入的節點
    def sendAll(self, message):
        for peer_mac in self.nodeMap.keys():
            print(f"send {peer_mac}")
            self.e.send(self.nodeMap[peer_mac], message)

    def broadcast(self, message):
        self.e.send(b'\xff\xff\xff\xff\xff\xff', message)
        #print("mac:"+ubinascii.hexlify(self.peer_mac).decode())

    def broadcast_mac(self):
        print(f"-> [ff:ff:ff:ff:ff:ff] cmd: {self.cmd(ESPNow.CMD_BOOT)}")
        self.e.send(b'\xff\xff\xff\xff\xff\xff', ESPNow.CMD_BOOT) # boot

    def recv(self, callback=None):
        self.callback = callback

    def irecv(self, recvTime):
        peer, msg = self.e.irecv(int(recvTime * 1000))
        if not msg == None:
            gc.collect()
            peer_str = ':'.join(f'{byte:02x}' for byte in peer)
            self.join(peer_str)
            if len(msg) == 2:
                print(f"<- [{peer_str}] cmd: {self.cmd(msg)}")
                if msg == ESPNow.CMD_RST:
                    machine.reset()
                    
                elif msg == ESPNow.CMD_STOP:
                    self.sendCmd(ESPNow.CMD_ACK, peer_str)
                    while True: self.irecv(1)

            elif len(msg) > 4 and msg[0:2] == ESPNow.CMD_JOIN:
                peer_str = msg[2:].decode()
                self.join(peer_str) # peer_str
            
            # 讓 8266 設定使用的 wifi channel
            elif len(msg) > 4 and msg[0:2] == ESPNow.CMD_CHANNEL:
                channel_str = msg[2:].decode()
                self.set_channel(channel_str) # peer_str
                
            elif len(msg) > 4 and msg[0:2] == ESPNow.CMD_FILE:
                print(f"<- [{peer_str}] cmd: {self.cmd(msg)}")
                # 这是内部控制指令（接收文件）
                chunk_size = msg[2]
                total_length = int.from_bytes(msg[3:7], 'big')
                end_of_filename = bytearray_find(msg, b'\n', 7)
                filename = msg[7:end_of_filename].decode()
                start_byte = int.from_bytes(msg[end_of_filename + 1:end_of_filename + 3], 'big')
                file_data = msg[end_of_filename + 3:]
                if filename not in self.file_buffer:
                    self.file_buffer[filename] = bytearray(total_length)
                self.file_buffer[filename][start_byte:start_byte + len(file_data)] = file_data
                # 检查是否所有区块都已接收
                #print(f"file: {(start_byte + len(file_data))} / {total_length}")
                if total_length == (start_byte + len(file_data)):
                    # 文件已完整，写入文件
                    with open(filename, 'wb') as f:
                        f.write(self.file_buffer[filename])
                    self.file_buffer = {}
                    gc.collect()
                    print("File " + filename + " written successfully")
                    self.sendCmd(ESPNow.CMD_FILE_WRITE_ACK, peer_str)
                    self.sendCmd(ESPNow.CMD_DONE, peer_str)
                else:
                    self.sendCmd(ESPNow.CMD_FILE_WRITE_ACK, peer_str)
            else:
                # 非内部控制指令，调用用户提供的回调
                if self.callback is not None:
                    self.callback(peer, msg)

def bytearray_find(haystack, needle, start=0):
    needle_len = len(needle)
    for i in range(start, len(haystack) - needle_len + 1):
        if haystack[i:i + needle_len] == needle:
            return i

