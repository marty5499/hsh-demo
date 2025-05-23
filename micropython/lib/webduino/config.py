import os, machine, json
from webduino.debug import debug

class Config:

    data = {}
    _key_order = ['board', '#comment_1', 'devId', 'devSSID', 'devPasswd',
                 '#comment_5', 'ssid1', 'passwd1', 'ssid2', 'passwd2',
                 'ssid3', 'passwd3', '#comment_12', 'openAp', 'zone',
                 'mqttServer', 'resolution', 'stream']

    def show():
        debug.DEBUG(f"{Config.data}")

    def put(key, val):
        Config.data[key] = val
        if key not in Config._key_order:
            Config._key_order.append(key)  # 確保新鍵被添加到 key_order 中
        return Config

    def get(key):
        return Config.data.get(key)

    def remove(key):
        if key in Config.data:
            del Config.data[key]
            if key in Config._key_order:
                Config._key_order.remove(key)  # 同步移除 key_order 中的鍵
            return True
        return False

    # index.html /save , default use mqtt-edu.webduino.io
    def updateFromString(data): 
        data = data.split('/')
        # 定義需要更新的鍵，排除註解和 'board'
        keys_to_update = ['ssid1', 'passwd1', 'ssid2', 'passwd2', 'ssid3', 'passwd3',
                          'devId', 'devSSID', 'devPasswd', 'zone', 'openAp', 'resolution', 'stream']
        
        for i, key in enumerate(keys_to_update):
            if i < len(data):
                Config.put(key, data[i])
            else:
                break
        Config.put('mqttServer', 'mqtt-edu.webduino.io')
        return Config.data

    def load(): 
        defaultData = "KingKit_MeetingRoom/webduino/////INTJ/cam03/12345678/global/Yes/res3/0"
        Config.data = {'mqttServer':'mqtt-edu.webduino.io'}
        Config._key_order = []
        try:
            with open('board.env','r') as file:
                for line in file:
                    # 去除首尾空白，保留註解行
                    line = line.rstrip('\n')
                    if not line or line.isspace():  # 跳過空行
                        continue
                    if line.lstrip().startswith('#'):  # 保存註解行
                        comment_key = f'#comment_{len(Config._key_order)}'
                        Config.data[comment_key] = line
                        Config._key_order.append(comment_key)
                        continue
                        
                    try:
                        # 用等号分割，maxsplit=1 确保值中的等号不会被分割
                        key, value = [x.strip() for x in line.split('=', 1)]
                        if not key:  # 確保鍵不為空
                            continue
                            
                        # 處理值：去除引號
                        value = value.strip()
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                            
                        Config.put(key, value)
                    except ValueError:
                        continue
        except Exception as e:
            debug.DEBUG(f"{e}")
            Config.updateFromString(defaultData)
            
        return Config.data

    def save():
        try:
            with open('board.env','w') as file:
                last_written = False  # 用於追蹤是否已經寫入內容
                # 按照原始順序遍歷所有鍵
                for key in Config._key_order:
                    if key.startswith('#comment_'):
                        # 如果上一行寫入了內容，且這是一個新的註解組，添加空行
                        if last_written:
                            file.write('\n')
                        file.write(f'{Config.data[key]}\n')
                        last_written = False
                    else:
                        value = Config.data[key]
                        # 決定是否需要加引號
                        needs_quotes = (
                            isinstance(value, str) and (
                                ' ' in value or 
                                value == '' or 
                                any(c in value for c in '=\'"#$%&*,;<>?[\\]^`{|}~')
                            )
                        )
                        # 對齊輸出
                        padding = ' ' * (8 - len(key))  # 假設最長的鍵是8個字符
                        if needs_quotes:
                            file.write(f'{key}{padding}= "{value}"\n')
                        else:
                            file.write(f'{key}{padding}= {value}\n')
                        last_written = True
                # 判斷如果沒有 mqttServer 則添加
                if 'mqttServer' not in Config.data:
                    file.write(f'mqttServer=mqtt-edu.webduino.io\n')
                debug.INFO(f"Config file save: {Config.data}")
            return Config.data
        except Exception as e:
            debug.DEBUG(f"{e}")
            return None


class JSONFile:
    
    def __init__(self,filename,default={}):
        self.filename = filename
        self.data = {}
        try:
            self.load()
        except:
            self.data = default
            self.save()

    def show(self):
        debug.INFO(f"{self.data}")

    def put(self,key,val):
        self.data[key] = val
        return self

    def get(self,key):
        return self.data.get(key)

    def remove(self,key):
        if key in self.data:
            del self.data[key]
            return True
        return False

    def load(self): 
        with open(self.filename,'r') as file:
            # 读取文件内容并用 json.loads 解析
            self.data = json.loads(file.read())
        return self.data

    def save(self):
        with open(self.filename,'w') as file:
            formatted_json = json.dumps(self.data, indent=2)
            file.write(formatted_json)
        return self.data