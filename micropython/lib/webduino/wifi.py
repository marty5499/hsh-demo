import network
import time
from machine import Timer
from webduino.debug import debug


class WiFi:
    onlineCallback = None
    ssid = "webduino.io"
    pwd = "webduino"
    ip = "unknown"

    def disconnect():
        WiFi.sta.disconnect()

    def check():
        pass  # print(WiFi.sta.isconnected())

    def onlilne(cb):
        WiFi.onlineCallback = cb

    def startKeepConnect():
        WiFi.timer = Timer(0)
        WiFi.timer.init(period=30000, mode=Timer.PERIODIC,
                        callback=WiFi.checkConnection)

    def checkConnection(t):
        if not WiFi.sta.isconnected():
            WiFi.connect(WiFi.ssid, WiFi.pwd)
            debug.DEBUG("!!!! online callback... !!!!")
        else:
            rssi = WiFi.sta.status('rssi')
            debug.DEBUG(f"WiFi signal strength: {rssi} dBm")
        return WiFi.sta.isconnected()

    def enableAP(ssid="myboard", pwd="12345678"):
        #print(f">>>> enableAP {ssid} / {pwd} <<<<<<")
        WiFi.ap = network.WLAN(network.AP_IF)
        WiFi.ap.active(True)
        WiFi.ap.config(essid=ssid, password=pwd, authmode=3)

    def connect(ssid="webduino.io", pwd="webduino", state_callback=None):
        """嘗試連接到WiFi，並在多次嘗試失敗後返回False
        
        每次嘗試最多持續5秒，總共嘗試3次
        如果都失敗，返回False讓上層方法嘗試下一個WiFi設定
        """
        WiFi.ssid = ssid
        WiFi.pwd = pwd
        WiFi.sta = sta_if = network.WLAN(network.STA_IF)
        sta_if.active(True)
        #sta_if.config(txpower=21)
        
        debug.DEBUG(f">>>>> txPower >>>> {sta_if.config('txpower')}")
        debug.DEBUG(f'嘗試連接網絡... {WiFi.ssid}')
        
        # 斷開任何現有連接
        sta_if.disconnect()
        
        if (WiFi.onlineCallback is not None):
            WiFi.onlineCallback(False)
        
        # 明確設定最大嘗試次數
        max_attempts = 3
        
        # 每次嘗試
        for attempt in range(max_attempts):
            debug.DEBUG(f"嘗試 {attempt+1}/{max_attempts}")
            
            # 啟動連接
            try:
                sta_if.connect(ssid, pwd)
            except Exception as e:
                debug.DEBUG(f"連接異常: {str(e)}")
                continue
            
            # 在這次嘗試中的每個計數
            cnt = 0
            max_counts = 10  # 5秒 (10 * 0.5秒)
            
            # 檢查連接狀態
            while cnt < max_counts:
                cnt += 1
                time.sleep(0.5)
                
                # 發送連接狀態回調
                if state_callback is not None:
                    state_callback(WiFi, ['wifi_connecting', cnt])
                
                # 檢查是否已連接
                if sta_if.isconnected():
                    # 成功連接
                    WiFi.ip = sta_if.ifconfig()[0]
                    rssi = sta_if.status('rssi')
                    
                    if state_callback is not None:
                        state_callback(WiFi, ['wifi_connected', rssi])
                    
                    debug.DEBUG(f"WiFi連接成功，信號強度: {rssi} dBm")
                    
                    if (WiFi.onlineCallback is not None):
                        WiFi.onlineCallback(True)
                    
                    return True
            
            # 這次嘗試失敗，斷開連接準備下次嘗試
            sta_if.disconnect()
            debug.DEBUG(f"連接嘗試 {attempt+1} 失敗")
        
        # 所有嘗試都失敗
        debug.DEBUG(f"無法連接到WiFi: {ssid}，所有嘗試都失敗")
        return False