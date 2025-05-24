import uasyncio
from webduino.webbit import WebBit

# 全域變數
current_distance = 0
servo_angle = 90
wbit = None

def process(topic, msg):
    """處理 MQTT 訊息的回調函數"""
    global servo_angle, wbit
    
    try:
        msg_str = msg.decode('utf-8')
        print(f"收到 MQTT 訊息 - Topic: {topic}, Message: {msg_str}")
        
        # 處理伺服馬達控制指令
        if topic == 'yyy/servo':
            import ujson
            data = ujson.loads(msg_str)
            
            # 檢查是否有角度參數
            if 'payload' in data and 'angle' in data['payload']:
                angle = data['payload']['angle']
                if 0 <= angle <= 180:
                    servo_angle = angle
                    # 控制伺服馬達轉動
                    wbit.sg90(9, servo_angle)
                    print(f"設定伺服馬達角度為: {servo_angle}°")
                    
                    # 顯示角度數字在 LED 矩陣上
                    if angle < 60:
                        wbit.matrix(100, 0, 0, "arrow_left")  # 紅色左箭頭
                    elif angle > 120:
                        wbit.matrix(0, 100, 0, "arrow_right")  # 綠色右箭頭
                    else:
                        wbit.matrix(0, 0, 100, "arrow_up")  # 藍色上箭頭
                else:
                    print(f"無效的角度值: {angle} (應為 0-180)")
            else:
                print("訊息格式錯誤：缺少 angle 參數")
                
    except Exception as e:
        print(f"處理 MQTT 訊息時發生錯誤: {e}")

async def read_ultrasonic():
    """讀取超音波感測器距離並發送 MQTT 訊息"""
    global current_distance, wbit
    
    while True:
        try:
            # 使用 pin1(trig) 和 pin2(echo) 讀取超音波距離
            distance = wbit.ultrasonic(1, 2)
            
            # 只有當距離變化超過 2cm 時才更新和發送
            if abs(distance - current_distance) > 2:
                current_distance = distance
                print(f"偵測到距離: {current_distance} cm")
                
                # 準備 MQTT 訊息 (符合 iotDevice.js 的格式)
                import ujson
                import urandom
                
                # 生成簡單的 requestId
                request_id = f"req-{urandom.getrandbits(16)}"
                
                mqtt_message = {
                    "requestId": request_id,
                    "from": "webbit-device",
                    "payload": {
                        "distance": current_distance
                    }
                }
                
                message_json = ujson.dumps(mqtt_message)
                
                # 發送 MQTT 訊息到 yyy/distance topic
                wbit.pub('yyy/distance', message_json)
                print(f"已發送 MQTT 訊息: {message_json}")
                
                # 根據距離控制 LED 顯示
                await display_distance_status(current_distance)
                
                # 根據距離自動調整伺服馬達角度
                await auto_servo_control(current_distance)
            
        except Exception as e:
            print(f"讀取超音波感測器時發生錯誤: {e}")
            wbit.matrix(100, 0, 0, "cry")  # 顯示錯誤圖示
        
        # 每 100ms 檢測一次
        await uasyncio.sleep_ms(100)

async def display_distance_status(distance):
    """根據距離顯示不同的 LED 狀態"""
    global wbit
    
    try:
        if distance < 10:
            # 距離很近 - 紅色警告
            wbit.matrix(100, 0, 0, "heart_1")
            # 播放警告音
            #wbit.play([[1000, 0.1], [800, 0.1]])
        elif distance < 30:
            # 距離適中 - 黃色
            wbit.matrix(100, 50, 0, "triangle_up")
        elif distance < 50:
            # 距離較遠 - 綠色
            wbit.matrix(0, 100, 0, "happy")
        else:
            # 距離很遠 - 藍色
            wbit.matrix(0, 0, 100, "star")
            
    except Exception as e:
        print(f"顯示距離狀態時發生錯誤: {e}")

async def auto_servo_control(distance):
    """根據距離自動控制伺服馬達角度"""
    global servo_angle, wbit
    
    try:
        # 根據距離自動調整角度 (距離越近，角度越小)
        if distance < 20:
            target_angle = 45  # 距離很近時向左轉
        elif distance < 40:
            target_angle = 90  # 距離適中時居中
        else:
            target_angle = 135  # 距離較遠時向右轉
        
        # 只有當角度變化較大時才調整
        if abs(target_angle - servo_angle) > 10:
            servo_angle = target_angle
            wbit.sg90(9, servo_angle)
            print(f"自動調整伺服馬達角度為: {servo_angle}°")
            
    except Exception as e:
        print(f"自動控制伺服馬達時發生錯誤: {e}")

async def button_control():
    """按鈕控制功能"""
    global wbit, servo_angle
    
    while True:
        try:
            # 檢查按鈕 A + B 同時按下 (優先判斷)
            if wbit.btnA() and wbit.btnB():
                print("按鈕 A+B 被按下 - 重置伺服馬達到中心位置")
                servo_angle = 90
                wbit.sg90(9, servo_angle)
                wbit.matrix(100, 100, 100, "tick")  # 顯示確認符號
                await uasyncio.sleep_ms(300)  # 防止重複觸發
                
            # 檢查單獨按下按鈕 A
            elif wbit.btnA():
                print("按鈕 A 被按下 - 伺服馬達向左轉")
                servo_angle = max(0, servo_angle - 15)  # 最小角度 0°
                wbit.sg90(9, servo_angle)
                wbit.matrix(0, 100, 100, "arrow_left")
                await uasyncio.sleep_ms(200)
                
            # 檢查單獨按下按鈕 B  
            elif wbit.btnB():
                print("按鈕 B 被按下 - 伺服馬達向右轉")
                servo_angle = min(180, servo_angle + 15)  # 最大角度 180°
                wbit.sg90(9, servo_angle)
                wbit.matrix(100, 100, 0, "arrow_right")
                await uasyncio.sleep_ms(200)
                
        except Exception as e:
            print(f"按鈕控制時發生錯誤: {e}")
        
        await uasyncio.sleep_ms(50)

async def status_monitor():
    """系統狀態監控"""
    global wbit
    
    while True:
        try:
            # 每 5 秒顯示一次系統狀態
            temp = wbit.temp()
            print(f"系統溫度: {temp}°C")
            print(f"目前距離: {current_distance} cm")
            print(f"伺服馬達角度: {servo_angle}°")
            print("=" * 30)
            
            # 檢查溫度警告
            if temp > 40:
                wbit.matrix(100, 0, 0, "hourglass")  # 溫度過高警告
                await uasyncio.sleep_ms(500)
            
        except Exception as e:
            print(f"狀態監控時發生錯誤: {e}")
        
        await uasyncio.sleep_ms(5000)

async def main():
    """主程式"""
    global wbit
    
    try:
        print("=== MQTT 超音波距離偵測系統啟動 ===")
        
        # 初始化 WebBit，啟用 MQTT 功能
        wbit = WebBit(mqtt=True)
        
        # 訂閱 MQTT topic 來接收伺服馬達控制指令
        wbit.sub('yyy/servo', process)
        
        # 初始化硬體
        print("初始化硬體組件...")
        
        # 設定伺服馬達初始位置 (90度，居中)
        wbit.sg90(9, 90)
        print("伺服馬達初始化完成")
        
        # 顯示啟動畫面
        wbit.matrix(0, 100, 0, "happy")
        await uasyncio.sleep_ms(1000)
        
        # 播放啟動音效
        #wbit.play([[262, 0.25], [294, 0.25], [330, 0.25], [349, 0.5]])
        
        print("系統初始化完成，開始運行...")
        
        # 並行執行多個任務
        await uasyncio.gather(
            read_ultrasonic(),      # 超音波距離偵測
            button_control(),       # 按鈕控制
            status_monitor(),       # 狀態監控
            mqtt_handler()          # MQTT 訊息處理
        )
        
    except Exception as e:
        print(f"主程式發生錯誤: {e}")
        # 錯誤時顯示錯誤圖示
        if wbit:
            wbit.matrix(100, 0, 0, "cry")

async def mqtt_handler():
    """MQTT 訊息處理循環"""
    global wbit
    
    while True:
        try:
            # 檢查是否有 MQTT 訊息
            await wbit.checkMsg()
        except Exception as e:
            print(f"MQTT 訊息處理時發生錯誤: {e}")
        
        await uasyncio.sleep_ms(10)

# 啟動主程式
print("正在啟動 MQTT 超音波距離偵測系統...")
uasyncio.run(main())
