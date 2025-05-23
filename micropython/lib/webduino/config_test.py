import uos as os
from lib.webduino.config import Config

def setup_test_env():
    # 設定測試用的 board.env 內容
    test_env_content = """board = agri

# device setting
devId    = agri001
devSSID  = agri001
devPasswd= 12345678

# wifi setting
ssid1   = KingKit_MeetingRoom
passwd1 = webduino
ssid2   = 
passwd2 = 
ssid3   = 
passwd3 = 

# mqtt setting
openAp = Yes
zone   = global
mqttServer=mqtt-agri.webduino.io
"""
    # 創建測試用的 board.env 文件
    with open('board.env', 'w') as f:
        f.write(test_env_content)

def teardown_test_env():
    # 測試完成後刪除 board.env 文件
    try:
        os.remove('board.env')
    except OSError:
        pass

def test_load():
    print("Running test_load...")
    data = Config.load()
    assert data.get('board') == 'agri', "board 應為 'agri'"
    assert data.get('devId') == 'agri001', "devId 應為 'agri001'"
    assert data.get('mqttServer') == 'mqtt-agri.webduino.io', "mqttServer 應為 'mqtt-agri.webduino.io'"
    print("test_load passed.")

def test_save():
    print("Running test_save...")
    Config.put('newKey', 'newValue')
    saved_data = Config.save()
    assert saved_data.get('newKey') == 'newValue', "newKey 應為 'newValue'"

    # 重新加載以確認保存
    Config.data = {}
    Config.load()
    assert Config.get('newKey') == 'newValue', "重新加載後 newKey 應為 'newValue'"
    print("test_save passed.")

def test_put_and_get():
    print("Running test_put_and_get...")
    Config.put('testKey', 'testValue')
    value = Config.get('testKey')
    assert value == 'testValue', "testKey 應為 'testValue'"
    print("test_put_and_get passed.")

def test_updateFromString():
    print("Running test_updateFromString...")
    update_string = "NewSSID/NewPasswd/AnotherSSID/AnotherPasswd/SSID3/Passwd3/devId002/devSSID002/devPasswd002/global/No/res4/1"
    updated_data = Config.updateFromString(update_string)
    assert updated_data.get('ssid1') == 'NewSSID', "ssid1 應為 'NewSSID'"
    assert updated_data.get('passwd1') == 'NewPasswd', "passwd1 應為 'NewPasswd'"
    assert updated_data.get('devId') == 'devId002', "devId 應為 'devId002'"
    assert updated_data.get('mqttServer') == 'mqtt-edu.webduino.io', "mqttServer 應為 'mqtt-edu.webduino.io'"
    print("test_updateFromString passed.")

def test_remove():
    print("Running test_remove...")
    Config.put('removeKey', 'removeValue')
    removed = Config.remove('removeKey')
    assert removed == True, "應成功移除 'removeKey'"
    assert Config.get('removeKey') is None, "'removeKey' 應為 None"

    # 嘗試移除不存在的鍵
    removed = Config.remove('nonExistentKey')
    assert removed == False, "移除不存在的鍵應返回 False"
    print("test_remove passed.")

def run_tests():
    setup_test_env()
    try:
        Config.load()  # 載入初始配置
        test_load()
        test_save()
        test_put_and_get()
        test_updateFromString()
        test_remove()
        print("所有測試均已通過！")
    except AssertionError as e:
        print("測試失敗:", e)
    finally:
        teardown_test_env()

if __name__ == '__main__':
    run_tests()