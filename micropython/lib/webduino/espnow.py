import espnow, ubinascii, network
import machine, time, gc

"""
# 2024/08/28
    - espnow 預設使用 channel=1 進行通訊
    - esp32 連上 wifi 後，會自動選擇 channel 
# 2024/08/22 fix broadcast func
# 2024/10/02
    - 修正廣播自動修改bit7造成無法比對
    - 增加可以傳送字串進行檔案傳送
"""
class ESPNow:

    def __init__(self, peer_str = None, sta=None, ap=None):
        ESPNow.CMD_STOP = b'\xf4\xfe'
        ESPNow.CMD_RST= b'\xff\xff'
        ESPNow.CMD_ACK= b'\xff\xfe'
        ESPNow.CMD_BOOT= b'\xff\x00'
        ESPNow.CMD_JOIN= b'\xff\x13'
        ESPNow.CMD_CHANNEL= b'\xff\x14'

        ESPNow.CMD_DONE= b'\xf4\x11'
        ESPNow.CMD_PUB= b'\xf4\x20'
        ESPNow.CMD_SUB= b'\xf4\x21'
        ESPNow.CMD_FILE= b'\xf4\x10'
        ESPNow.CMD_FILE_WRITE_ACK= b'\xf4\x12'

        if sta == None and ap == None:
            self.sta, self.ap = self.wifi_reset()
        else:
            self.sta = sta
            self.ap = ap

        self.e = espnow.ESPNow() 
        self.e.active(True)

        if not peer_str == None:
            if isinstance(peer_str, bytes):
                self.peer_mac = peer_str
                hex_string = ''.join(f'{byte:02x}' for byte in peer_str)
                print(f"join {peer_str}:{hex_string}")
            else:
                peer_hex = ''.join('{:02x}'.format(ord(char)) for char in peer_str)
                peer_mac = ubinascii.unhexlify(peer_hex)
                if len(peer_mac) != 6:
                    raise ValueError("ESPNow: bytes or bytearray wrong length")
                formatted_hex = ''.join(f'\\x{peer_hex[i:i+2]}' for i in range(0, len(peer_hex), 2))
                print(f"join {peer_str}:{formatted_hex}")
                self.peer_mac = peer_mac
        else:
            self.peer_mac = network.WLAN().config('mac') # 6byte

        self.e.add_peer(self.peer_mac)
        self.peer_mac_str = (ubinascii.hexlify(self.peer_mac, ':').decode())
        print(f"[Mac] {self.peer_mac_str} [ch] {self.channel()}")
        self.file_buffer = {}
        self.nodeMap = {}
        self.cmdMap = {}

    def channel(self):
        return self.ap.config('channel')

    def wifi_reset(self):
        ap = network.WLAN(network.AP_IF)
        ap.active(False)
        ap.active(True)
        sta = network.WLAN(network.STA_IF)
        sta.active(False)
        sta.active(True)
        while not sta.active():
            time.sleep(0.1)
        return sta, ap

    def cmd(self,msg):
        if msg == ESPNow.CMD_STOP:
            return "STOP"
        elif msg == ESPNow.CMD_RST:
            return "RST"
        elif msg == ESPNow.CMD_PUB:
            return "PUB"
        elif msg == ESPNow.CMD_SUB:
            return "SUB"
        elif msg == ESPNow.CMD_BOOT:
            return "BOOT"
        elif msg == ESPNow.CMD_FILE:
            return "FILE"
        elif msg == ESPNow.CMD_JOIN:
            return "JOIN"
        elif msg == ESPNow.CMD_DONE:
            return "DONE"
        elif msg == ESPNow.CMD_FILE_WRITE_ACK:
            return "FILE_WRITE_ACK"
        elif msg == ESPNow.CMD_ACK:
            return "ACK"
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

    def send(self, peer_mac_str, msg):
        if peer_mac_str in self.nodeMap:
            self.e.send(self.nodeMap[peer_mac_str], msg)
            #print(f"send: {peer_mac_str}: {msg}")

    def sendJoin(self,to_peer_mac_str, data_peer_str):
        if to_peer_mac_str in self.nodeMap:
            message = bytearray(ESPNow.CMD_JOIN)
            message.extend(data_peer_str)
            self.e.send(self.nodeMap[to_peer_mac_str], message )

    def sendCmd(self, cmd , peer_mac_str):
        if peer_mac_str in self.nodeMap:
            self.e.send(self.nodeMap[peer_mac_str], cmd)
            print(f"-> {self.cmd(cmd)} [{peer_mac_str}]")
            
    def sendAll(self, message):
        for peer_mac_str in self.nodeMap.keys():
            self.e.send(self.nodeMap[peer_mac_str], message)

    def broadcast(self, message):
        self.e.add_peer(b'\xff\xff\xff\xff\xff\xff')
        self.e.send(b'\xff\xff\xff\xff\xff\xff', message)
        self.e.del_peer(b'\xff\xff\xff\xff\xff\xff')
        #print("mac:"+ubinascii.hexlify(self.peer_mac).decode())

    def broadcast_mac(self):
        self.broadcast('rst '+self.peer_mac_str)

    def recvCmd(self, cmd, peer_str):
        self.cmdMap[peer_str] = cmd
        while peer_str in self.cmdMap:
            time.sleep(0.01)

    def recv(self, callback=None):
        def bytearray_find(haystack, needle, start=0):
            needle_len = len(needle)
            for i in range(start, len(haystack) - needle_len + 1):
                if haystack[i:i + needle_len] == needle:
                    return i
            return -1
        def internal_recv_callback(*args):
            print("incoming...")
            if len(args) ==1:
                code = 1 # nonuse
                peer, msg = args[0].recv()
            else:
                code = args[0]
                peer, msg = args[1]

            proc_peer = bytearray(peer)
            proc_peer[0] = proc_peer[0] & 0b11111101
            peer_str = ':'.join(f'{byte:02x}' for byte in proc_peer)

            if len(msg) == 2 and msg[0] & 0xf0 == 0xf0:
                print(f"<- [{peer_str}] cmd: {self.cmd(msg)}")

                if msg == ESPNow.CMD_RST:
                    machine.reset()

                elif msg == ESPNow.CMD_BOOT:
                    self.join(peer) # 通知開機的peer加入本身peer
                    print(f"set {peer_str} to join....{self.peer_mac_str}")
                    self.sendJoin(peer_str, self.peer_mac_str)
                    if peer_str in self.cmdMap and self.cmdMap[peer_str] == ESPNow.CMD_BOOT:
                        print(f"del {self.cmdMap[peer_str]}")
                        del self.cmdMap[peer_str]
                    #self.sendCmd(ESPNow.CMD_STOP, peer_str)

                elif msg == ESPNow.CMD_ACK:
                    if peer_str in self.cmdMap and self.cmdMap[peer_str] == ESPNow.CMD_ACK:
                        del self.cmdMap[peer_str]
                    
                elif msg == ESPNow.CMD_DONE:
                    if peer_str in self.cmdMap and self.cmdMap[peer_str] == ESPNow.CMD_DONE:
                        del self.cmdMap[peer_str]

                elif msg == ESPNow.CMD_FILE_WRITE_ACK:
                    if peer_str in self.cmdMap and self.cmdMap[peer_str] == ESPNow.CMD_FILE_WRITE_ACK:
                        del self.cmdMap[peer_str]

                elif len(msg) > 4 and msg[0:2] == ESPNow.CMD_PUB:
                    topic_pub = msg[3:] # topicName , data
                    # ...

                elif len(msg) > 4 and msg[0:2] == ESPNow.CMD_SUB:
                    topic_sub = msg[3:] # topicName
                    # ...

                elif len(msg) > 4 and msg[0:2] == ESPNow.CMD_JOIN:
                    self.join(msg[3:])

                elif len(msg) > 4 and msg[0:2] == ESPNow.CMD_FILE:
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
                    if total_length == (start_byte + len(file_data)):
                        # 文件已完整，写入文件
                        with open(filename, 'wb') as f:
                            f.write(self.file_buffer[filename])
                        print("File " + filename + " written successfully")
                        self.sendCmd(ESPNow.CMD_DONE, peer_str)
                    
            if callback is not None:
                callback(peer, msg, self.e.peers_table)
            #"""
        self.e.irq(internal_recv_callback)
        
    def entryCmdMode(self,peer_mac_str):
        self.join(peer_mac_str)
        self.sendCmd(ESPNow.CMD_RST, peer_mac_str)
        self.recvCmd(ESPNow.CMD_BOOT, peer_mac_str)
        self.sendCmd(ESPNow.CMD_STOP, peer_mac_str)
        self.recvCmd(ESPNow.CMD_ACK, peer_mac_str)

    def sendSyncFile(self, peer_mac_str, file_path, target_file, chunk_size, callback=None):
        self.entryCmdMode(peer_mac_str)
        self.sendFile(peer_mac_str, file_path, target_file, chunk_size, callback)

    def sendSyncFileContent(self, peer_mac_str, file_content, target_file, chunk_size, callback=None):
        self.entryCmdMode(peer_mac_str)
        self.sendFileContent(peer_mac_str, file_content, target_file, chunk_size, callback)

    def sendFileContent(self, peer_mac_str, file_content, target_file, chunk_size, callback=None):
        #self.join(peer_mac_str)
        total_length = len(file_content)
        total_chunks = (total_length + chunk_size - 1) // chunk_size
        for chunk_index in range(total_chunks):
            start_byte = chunk_index * chunk_size
            end_byte = min(start_byte + chunk_size, total_length)
            chunk_data = file_content[start_byte:end_byte]
            message = bytearray(ESPNow.CMD_FILE)
            message.append(chunk_size)  # 這邊加入此次傳送的 chunk_size
            message.extend(total_length.to_bytes(4, 'big'))  # 修正這裡，傳送總長度
            message.extend(target_file.encode() + b'\n')
            message.extend(start_byte.to_bytes(2, 'big'))
            message.extend(chunk_data)
            self.send(peer_mac_str, message)
            # wait response
            self.recvCmd(ESPNow.CMD_FILE_WRITE_ACK, peer_mac_str)
            if callback is not None:
                callback(peer_mac_str , end_byte , total_length)
        gc.collect()

    def sendFile(self, peer_mac_str, file_path, target_file, chunk_size, callback=None):
        with open(file_path, 'rb') as f:
            file_content = f.read()
        self.sendFileContent(peer_mac_str, file_content, target_file, chunk_size, callback)

    def cmd_reset(self):
        message = bytearray([0xf4, 0xff])
        self.send(message)
        print("Reset command sent")
