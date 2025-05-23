from webduino.wifi import WiFi
from webduino.mqtt import MQTT
from webduino.config import Config
from webduino.debug import debug
from webduino.webserver import WebServer
import time, uasyncio, machine, os, builtins, ubinascii, network

original_print = builtins.print
# 定義自訂的 print 方法

def custom_print(*args, **kwargs):
    modified_args = args
    if 'board' in globals():
        try:
            message = ' '.join(map(str, args))
            # 判斷 message 開頭是 ! 才傳送
            if message.startswith('!'):
                board.mqtt.pub(f'waboard/{board.devId}/output', message)
        except:
            pass
    original_print(*modified_args, **kwargs)


builtins.print = custom_print

"""
2024/09/06 修正wifi設定空字串，導致無法重新設定wifi
2024/11/28 
 - 修正cmd 接收處理 , ping , info , code , save ,reset , reboot test ok
 - 修正 board 增加訂閱主題會導致無法接收cmd的問題
2024/12/02
 - 優化 cmd report 一致性
2024/12/16
 - 增加 cmd == 'delete' 功能
 - 參數設定 values.js 改用 board.env
 - board.env 增加設定 mqttServer , 如果沒設定預設是 mqtt1.webduino.io
2025/04/07
 - 修正 code 執行時，如果code開頭是#AFTER_RESTART，則重啟設備
 - 修正 WiFi 內建 webduino.io
"""


class Board:

    Ver = '0.3.2'

    def __init__(self, devId='', mqtt=False, mqttServer='', topic_report='waboard/state', topic_report_msg='disconnect', state_callback=None):
        debug.off()
        self.wifi = WiFi
        self.mqtt = MQTT
        self.wifi.onlilne(self.online)
        self.config = Config
        self.state_callback = state_callback
        self.now = 0
        self.devices = []
        json = self.config.load()
        # 判斷 json['mqttServer'] 是否為空
        if json['mqttServer'] == '':
            self.mqttServer = 'mqtt1.webduino.io'
        else:
            self.mqttServer = json['mqttServer']
        if (devId == ''):
            devId = json['devId']
        json['devId'] = devId
        debug.print("Device ID:"+devId)
        self.topic_report = f"{topic_report}/{devId}"
        self.topic_report_msg = topic_report_msg
        self.config.save()
        self.devId = devId
        self.devPasswd = json['devPasswd']
        if self.state_callback != None:
            self.state_callback(self, ['cfg',''])
        #self.enableAP()
        if mqtt:
            # 嘗試連接WiFi，但不要在連接失敗時重啟（讓connect方法處理）
            try:
                self.connect(ssid=json['ssid1'], pwd=json['passwd1'])
                # 只有成功連接後才設置AP的名稱
                apName = self.config.data['devSSID']+'_'+self.ip()
                self.wifi.ap.config(
                    essid=apName, password=self.config.data['devPasswd'], authmode=3)
                debug.print('board IP:'+self.ip())
            except Exception as e:
                debug.print(f"初始化WiFi連接時發生錯誤: {str(e)}")
        globals()['board'] = self

    def ap(self):
        return self.wifi.ssid

    def ip(self):
        return self.wifi.ip

    def mac(self):
        return ubinascii.hexlify(network.WLAN().config('mac'), ':').decode()

    def enableAP(self):
        ssid = self.config.data['devSSID']
        pwd = self.config.data['devPasswd']
        
        # 關閉現有的 web server（如果存在）
        if hasattr(self.wifi, 'web') and self.wifi.web:
            try:
                self.wifi.web.ss.close()
            except:
                pass
            self.wifi.web = None
        # 等待一下讓系統釋放端口
        time.sleep(0.1)
        
        self.wifi.enableAP(ssid, pwd)
        self.wifi.web = WebServer(self, 80)
        self.wifi.web.listener()
        debug.print("webServer start...")

    def online(self, status):
        if status:
            self.mqtt.server = self.mqttServer
            self.mqtt.topic_report = self.topic_report
            self.mqtt.topic_report_msg = self.topic_report_msg
            self.mqtt.connect()
            debug.print("connect mqtt...OK")
        else:
            debug.print("offline...")
            pass

    def connect(self, ssid='webduino.io', pwd='webduino'):
        """嘗試連接多個WiFi網絡，按優先順序嘗試
        
        先嘗試使用提供的 ssid/pwd (通常是ssid1/passwd1)
        如果連接失敗，嘗試 ssid2/passwd2 (如果不為空)
        如果連接失敗，嘗試 ssid3/passwd3 (如果不為空)
        如果還是連接失敗，使用預設的 webduino.io/webduino
        每個 WiFi 嘗試 3 次
        如果所有嘗試都失敗，重啟設備
        """
        # 獲取設定的WIFI配置
        wifi_configs = [
            {'ssid': ssid, 'pwd': pwd},  # 傳入的第一個WiFi配置
            {'ssid': self.config.data.get('ssid2', ''), 'pwd': self.config.data.get('passwd2', '')},
            {'ssid': self.config.data.get('ssid3', ''), 'pwd': self.config.data.get('passwd3', '')},
            {'ssid': 'webduino.io', 'pwd': 'webduino'}  # 預設備用配置
        ]
        
        # 只保留有效的WiFi配置（SSID非空）
        valid_configs = [config for config in wifi_configs if config['ssid']]
        
        # 如果所有配置都無效，則使用預設配置
        if not valid_configs:
            valid_configs = [{'ssid': 'webduino.io', 'pwd': 'webduino'}]
        
        # 嘗試每個WiFi配置
        for config in valid_configs:
            current_ssid = config['ssid']
            current_pwd = config['pwd']
            print(f"嘗試連接WiFi: {current_ssid}")
            
            # 每個WiFi嘗試3次
            for attempt in range(3):
                print(f"連接嘗試 {attempt+1}/3")
                try:
                    # 調用WiFi.connect並檢查返回值
                    connect_result = self.wifi.connect(current_ssid, current_pwd, self.state_callback)
                    if connect_result == True:
                        # 連接成功
                        debug.INFO(f"WiFi {current_ssid} Ready , MQTT Ready , ready to go...")
                        # 限制只能接收訂閱 ${deviceId} 底下
                        self.mqtt.sub(self.devId+"-cmd", self.execCmd)
                        self.report('boot')
                        return self
                    elif connect_result == False:
                        # WiFi.connect明確返回失敗，不再嘗試當前配置，直接嘗試下一個
                        print(f"WiFi連接返回失敗: {current_ssid}，嘗試下一個配置")
                        break
                    # 如果connect_result不是布爾值(可能是None)，繼續嘗試
                except Exception as e:
                    print(f"連接錯誤: {str(e)}")
                
                # 短暫延遲後重試
                time.sleep(1)
        
        # 如果所有配置都嘗試失敗，重啟設備
        print("所有WiFi配置連接失敗，重啟設備...")
        machine.reset()
        return self

    def sub(self, topic, cb):
        self.mqtt.sub(topic, cb)

    def pub(self, topic, msg, retain=False,qos=0):
        self.mqtt.pub(topic, msg, retain)

    def ping(self):
        self.mqtt.client.ping()

    def report(self, cmd):
        #debug.print(f"waboard/{self.devId}/ack {cmd}")
        debug.print(f"waboard/{self.devId}/ack {len(cmd)}")
        self.mqtt.pub(f"waboard/{self.devId}/ack", cmd)
        debug.print("publish OK")

    def execCmd(self, topic, data):
        dataArgs = data.decode('UTF-8').split(' ')
        debug.print("exceCmd:", dataArgs)
        cmd = dataArgs[0]
        try:
            if cmd == 'reboot':
                self.report('reboot')
                time.sleep(1)
                debug.print("restart...")
                machine.reset()

            elif cmd == 'ping':
                self.report('ping pong')

            elif cmd == 'info':
                import sys
                import gc
                import os
                import json
                version = sys.version
                rssi = self.wifi.sta.status('rssi')
                ip = self.wifi.sta.ifconfig()[0]
                total_mem = (gc.mem_alloc() + gc.mem_free()) / \
                    1024  # Convert to KB
                free_mem = gc.mem_free() / 1024  # Convert to KB
                storage_stats = os.statvfs('/')
                block_size = storage_stats[0]  # Block size
                total_blocks = storage_stats[2]  # Total blocks
                free_blocks = storage_stats[3]  # Free blocks
                total_storage = (block_size * total_blocks) / 1024  # Convert to KB
                free_storage = (block_size * free_blocks) / 1024  # Convert to KB
                main_first_line = "Not found"
                boot_first_line = "Not found"
                try:
                    with open('main.py', 'r') as f:
                        main_first_line = f.readline().strip()
                except:
                    pass

                try:
                    with open('boot.py', 'r') as f:
                        boot_first_line = f.readline().strip()
                except:
                    pass

                # Create info dictionary
                info_dict = {
                    "micropython": version,
                    "network": {
                        "ip": ip,
                        "wifi_signal": rssi
                    },
                    "memory": {
                        "total": round(total_mem, 2),
                        "free": round(free_mem, 2),
                        "unit": "KB"
                    },
                    "storage": {
                        "total": round(total_storage, 2),
                        "free": round(free_storage, 2),
                        "unit": "KB"
                    },
                    "files": {
                        "main.py": main_first_line,
                        "boot.py": boot_first_line
                    }
                }

                # Convert to JSON string
                info_json = json.dumps(info_dict)

                self.report(f'info {info_json}')
                debug.print(f"System info: {info_json}")

            elif cmd == 'code':
                try:
                    import json
                    if len(dataArgs) < 2:
                        response = {
                            'state': False,
                            'err': 'No code provided',
                            'output': ''
                        }
                        self.report(f'code {str(response)}')
                        return

                    code = ' '.join(dataArgs[1:])
                    debug.print("Executing code:", code)

                    # 設置執行標誌
                    global _EXECUTING_CODE
                    _EXECUTING_CODE = True

                    try:
                        # 執行代碼
                        exec(code)
                    finally:
                        # 確保標誌被重置
                        _EXECUTING_CODE = False

                    response = {
                        'state': True,
                        'err': '',
                        'output': ''
                    }
                    # 將結果轉換為 JSON 字串並回傳
                    result = json.dumps(response)
                    self.report(f'code {result}')
                    # 如果code開頭是#AFTER_RESTART，則重啟設備
                    if code.startswith('#AFTER_RESTART'):
                        # 创建非同步任務來處理重啟操作
                        uasyncio.create_task(self._delayed_reset(2))
                        
                    response = {
                        'state': True,
                        'err': '',
                        'output': ''
                    }
                    # 將結果轉換為 JSON 字串並回傳
                    result = json.dumps(response)
                    self.report(f'code {result}')

                except Exception as e:
                    debug.print("Code execution error:", str(e))
                    response = {
                        'state': False,
                        'err': str(e),
                        'output': ''
                    }
                    result = json.dumps(response)
                    self.report(f'code {result}')

            elif cmd == 'read':
                try:
                    filepath = dataArgs[1]
                    read_seek = int(dataArgs[2])
                    chunk_size = int(dataArgs[3])
                    print(f" >>> chunk size: {chunk_size}")
                    # 先取得檔案大小
                    #import os
                    #file_size = os.stat(filepath)[6]  # 取得檔案大小
                    #self.report(f"read size {file_size}")

                    # 只讀取指定位置的區塊
                    import ubinascii
                    with open(filepath, 'rb') as f:
                        f.seek(read_seek)  # 移動到指定位置
                        chunk = f.read(chunk_size)  # 讀取指定大小的區塊
                        # 使用 ubinascii.b2a_base64() 進行編碼，並移除結尾的換行符
                        encoded_chunk = ubinascii.b2a_base64(
                            chunk).decode('utf-8').rstrip()
                        self.report(f"read data {encoded_chunk}")
                        time.sleep(1)

                except Exception as e:
                    self.report(f"read error {str(e)}")

            elif cmd == 'list':
                try:
                    import os
                    import json

                    # 如果没有提供路径默认为根目录
                    path = dataArgs[1] if len(dataArgs) > 1 else '/'

                    # 确保路径以 / 结尾
                    if not path.endswith('/'):
                        path += '/'

                    result_list = []
                    # 将当前路径作为第一个元素
                    result_list.append(path)

                    # 遍历目录
                    for entry in os.ilistdir(path):
                        name = entry[0]
                        type_id = entry[1]
                        
                        # 确定文件类型
                        entry_type = 'd' if type_id == 0x4000 else 'f'
                        
                        # 获取文件大小
                        size = 0
                        if entry_type == 'f':
                            try:
                                size = os.stat(path + name)[6]
                            except:
                                size = 0
                        
                        # 添加 [类型, 名称, 大小] 的数组
                        result_list.append([entry_type, name, size])

                    # 将结果转换为 JSON 字符串并返回
                    result = json.dumps(result_list)
                    self.report(f'list {result}')

                except Exception as e:
                    error_msg = f'List command failed: {str(e)}'
                    debug.print(error_msg)
                    self.report(f'list error: {error_msg}')

            elif cmd == 'save':
                try:
                    # 檢查是否有檔案名稱參數
                    if len(dataArgs) < 3:  # save <path> <command>
                        self.report('error:Invalid save command format')
                        return

                    filepath = dataArgs[1]  # 取得檔案路徑
                    subcmd = dataArgs[2]    # 取得子命令 (size/data/complete)

                    # 處理檔案大小資訊
                    if subcmd.startswith('size:'):
                        try:
                            self.file_size = int(subcmd.split(':')[1])
                            self.bytes_received = 0

                            # 確保目標目錄存在
                            try:
                                import os
                                parts = filepath.split('/')[:-1]
                                if parts:
                                    current_path = ''
                                    for part in parts:
                                        if part:
                                            current_path += '/' + part if current_path else part
                                            try:
                                                os.mkdir(current_path)
                                            except OSError:
                                                pass
                            except Exception as e:
                                self.report(f'error:Failed to create directory: {str(e)}')
                                return

                            # 開啟檔案準備寫入
                            try:
                                self.file = open(filepath, 'wb')
                                self.filepath = filepath
                                self.report('ready')
                            except OSError as e:
                                self.report(f'error:Failed to open file: {str(e)}')
                            return
                        except ValueError as e:
                            self.report(f'error:Invalid file size format: {str(e)}')
                            return

                    # 處理檔案內容
                    if subcmd.startswith('data'):
                        if not hasattr(self, 'file'):
                            self.report('error:No file transfer initiated')
                            return

                        try:
                            # 解析 seek 位置和資料
                            parts = subcmd.split(' ', 1)
                            if len(parts) == 2:
                                seek_pos = int(parts[0].split(':')[1])
                                data = parts[1]
                            else:
                                seek_pos = self.bytes_received
                                data = subcmd[5:]  # 跳過 'data:' 前綴

                            # 設定檔案指標位置
                            self.file.seek(seek_pos)
                            
                            # 解碼並寫入資料
                            import ubinascii
                            chunk = ubinascii.a2b_base64(data)
                            self.file.write(chunk)
                            self.bytes_received = max(self.bytes_received, seek_pos + len(chunk))
                            
                            # 回報寫入成功
                            self.report(f'write {seek_pos} {len(chunk)}')
                        except Exception as e:
                            self.file.close()
                            del self.file
                            self.report(f'error:Failed to write chunk: {str(e)}')
                        return

                    # 處理完成訊息
                    if subcmd.startswith('complete'):
                        if not hasattr(self, 'file'):
                            self.report('error:No file transfer initiated')
                            return

                        try:
                            # 檢查是否有指定最終大小
                            parts = subcmd.split(':')
                            final_size = int(parts[1]) if len(parts) > 1 else self.file_size

                            # 關閉檔案
                            self.file.close()

                            # 檢查檔案大小
                            import os
                            actual_size = os.stat(self.filepath)[6]
                            if actual_size != final_size:
                                self.report(f'error:Size mismatch. Expected {final_size}, got {actual_size}')
                                return

                            # 清理資源
                            del self.file
                            del self.file_size
                            del self.bytes_received

                            self.report(f'save success {self.filepath}')
                        except Exception as e:
                            self.report(f'error:Failed to complete file: {str(e)}')
                        return

                except Exception as e:
                    if hasattr(self, 'file'):
                        self.file.close()
                        del self.file
                    self.report(f'error:Save operation failed: {str(e)}')

            elif cmd == 'time':
                if len(dataArgs) < 2:
                    self.report('error:No timestamp provided')
                    return
                from lib.clock import Clock
                timestamp = int(dataArgs[1])
                self.clock = Clock(timestamp)
                current_time = self.clock.get()
                self.report(f'time {current_time}')
                self.state_callback(self,['time',current_time])
                debug.print(f"Time set to: {current_time} , callback...")

            elif cmd == 'delete':
                try:
                    if len(dataArgs) < 2:
                        self.report('error:No file path provided')
                        return
                    import os
                    filepath = dataArgs[1]
                    try:
                        # 嘗試作為檔案刪除
                        os.remove(filepath)
                        debug.print(f"File deleted: {filepath}")
                        self.report(f'delete ok')
                    except OSError:
                        os.rmdir(filepath)
                        debug.print(f"Directory deleted: {filepath}")
                        self.report(f'delete success {filepath}')
                except Exception as e:
                    error_msg = f'Delete command failed: {str(e)}'
                    debug.print(error_msg)
                    self.report(f'delete error: {error_msg}')
        except Exception as e:
            debug.print(f"execCmd error: {str(e)}")
            self.report(f'execCmd error: {str(e)}')

    async def _delayed_reset(self, delay_seconds):
        """非同步延遲重啟函數"""
        await uasyncio.sleep(delay_seconds)
        machine.reset()