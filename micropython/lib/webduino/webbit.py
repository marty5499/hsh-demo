import machine
import neopixel
import time
import math
import micropython
from machine import ADC, Pin
from webduino.board import Board
from webduino.debug import debug
from webduino.image import get_array
from webduino.image import get_image
from webduino.hcsr04 import HCSR04
from webduino.sg90 import SG90
from webduino.vibrationSensor import _VibrationSensor
from webduino.soundSensor import SoundSensor
from webduino.touch import Touch
from dht import DHT11

class Temp():
    def __init__(self):
        self.voltagePower = 3.3
        self.Rs = 10000   # 更改 Rs 的值，根據您的熱敏電阻的規格表
        self.B = 3950
        self.T0 = 273.15
        self.R1 = 2500   # 更改 R1 的值，根據傳感器上的參考電阻的規格表
        self.__temp__ = ADC(Pin(14))  # 溫度傳感器
        self.__temp__.atten(ADC.ATTN_11DB)
        self.lastTemp = 0

    def read(self):
        self.voltageValue = (self.__temp__.read() / 4095) * self.voltagePower
        self.Rt = ((self.voltagePower - self.voltageValue)
                   * self.Rs) / self.voltageValue
        try:
            T = 1 / ((1 / self.T0) + (1 / self.B) *
                     math.log(self.Rt*2 / self.R1))
            self.lastTemp = T - self.T0
        except:
            pass
        return self.lastTemp

class Btn():
    def __init__(self, pinNum):
        # A:35 , B:27
        self.btn = Pin(pinNum, Pin.IN)
        self.down = False
        self.up = False

    def isDown(self):
        down = self.btn.value() == 0
        if down:
            if self.down:
                return False
            self.down = True
            self.up = True
            return self.down
        else:
            if self.down:
                self.down = False
            return False

    def isUp(self):
        if self.btn.value() == 1 and self.up:
            self.up = False
            return True
        return False

class Buzzer:
    # 262 294 330 349 392 440 494
    def __init__(self):
        self.queue = []

    def playOne(self, freq=300, duration=0.1):
        if freq == 0:
            freq = 1
        pin17 = machine.PWM(machine.Pin(17), freq=freq, duty=512)
        if (duration == -1):
            return
        if (duration >= 10):
            duration = duration/1000.0
        time.sleep(duration)
        machine.PWM(machine.Pin(17), duty=0)

    def playList(self, lst):
        self.queue.extend(lst)

    def stop(self):
        self.queue = []
        self.playOne(1, 10)

    def run(self):
        while len(self.queue) > 0:
            note = self.queue[0]
            del self.queue[0]
            if isinstance(note, int):
                duration = self.queue[0]
                del self.queue[0]
                self.playOne(note, duration)
            else:
                self.playOne(note[0], note[1])

    def play(self, *args):
        if len(args) == 1 and isinstance(args[0], list):
            # Input: [ [freq1, delay1], [freq2, delay2], ... ]
            # print('1')
            for i in args:
                self.queue.extend(args[0])
            print(self.queue)
        elif len(args) == 1 and isinstance(args[0], int):
            self.playOne(args[0], -1)
        elif len(args) == 2 and isinstance(args[0], int) and isinstance(args[1], (int, float)):
            # Input: freq, delay
            # print('2')
            self.queue.append([args[0], args[1]])
        self.run()

class RGB:
    def __init__(self, wbit, num):
        self.num = num
        self.wbit = wbit

    def color(self, r, g, b):
        self.wbit.show(self.num, r, g, b)

    def off(self):
        self.wbit.show(self.num, 0, 0, 0)

class WebBit(Board):
    LOG_LEVELS = {
        'DEBUG': 10,
        'INFO': 20,
        'WARN': 30,
        'ERROR': 40
    }

    def close(self):
        pass

    def disconnect(self):
        pass

    def createRGB(self):
        self.rgb = []
        for i in range(25):
            self.rgb.append(RGB(self, i))

    def __init__(self, devId='', mqtt=False,topic_report='waboard/state', topic_report_msg='disconnect',log_level='INFO',state_callback=None):
        self.current_log_level = log_level  # 預設日誌級別
        self.np = neopixel.NeoPixel(machine.Pin(18), 25)
        self.buzzer = Buzzer()
        self.a = Btn(38)
        self.b = Btn(33)
        self.lL = ADC(Pin(12))
        self.rL = ADC(Pin(13))
        self.lL.atten(ADC.ATTN_6DB)
        self.rL.atten(ADC.ATTN_6DB)
        self.devId = devId
        self._temp = Temp()
        self.debug = debug
        self.createRGB()
        self.showAll(250, 10, 10)        
        self._hcsr04 = None
        self._sg90_motors = {} # 初始化 SG90 馬達物件字典
        self._sound_sensors = {} # Initialize dictionary for sound sensors
        self._vibration_sensors = {}
        self.wled = {0: 20, 1: 15, 2: 10, 3: 5, 4: 0, 5: 21, 6: 16, 7: 11, 8: 6, 9: 1, 10: 22, 11: 17,
                     12: 12, 13: 7, 14: 2, 15: 23, 16: 18, 17: 13, 18: 8, 19: 3, 20: 24, 21: 19, 22: 14, 23: 9, 24: 4}
        super().__init__(devId, mqtt, topic_report=topic_report, topic_report_msg=topic_report_msg,state_callback=state_callback)
        self.showAll(0, 0, 0)
        self.beep()

    def setLogLevel(self, level):
        """設置日誌顯示級別 level (str): 日誌級別 ('DEBUG', 'INFO', 'WARN', 'ERROR')
        """
        if level in self.LOG_LEVELS:
            self.current_log_level = level
            self.log('INFO', f"Log level set to: {level}")
        else:
            self.log('ERROR', f"Invalid log level: {level}")

    def log(self, level='INFO', message=''):
        """記錄訊息
        Args:
            level (str): 日誌級別 ('DEBUG', 'INFO', 'WARN', 'ERROR')
            message (str): 要記錄的訊息
        """
        if not message:  # 如果訊息為空，直接返回
            return
        # 當日誌級別大於於當前設置的級別時才顯示
        if self.LOG_LEVELS[level] >= self.LOG_LEVELS[self.current_log_level]:
            print(f"{level}: {message}")

    async def checkMsg(self):
        await self.mqtt.checkMsg()

    def readTemp(self):
        return self._temp.read()

    def temp(self):
        return self._temp.read()

    def leftLight(self):
        return self.lL.read()

    def rightLight(self):
        return self.rL.read()

    def readLeftLight(self):
        return self.lL.read()

    def readRightLight(self):
        return self.rL.read()

    def btnA(self):
        return self.a.btn.value() == 0

    def btnB(self):
        return self.b.btn.value() == 0

    def play(self, *args):
        self.buzzer.play(*args)

    def buzz(self, *args):
        self.buzzer.play(*args)

    def tone(self, *args):
        self.buzzer.play(*args)

    def beep(self, *args):
        if (len(args) == 0):
            self.buzzer.play(500, 100)
        else:
            self.buzzer.play(*args)

    def touchP0(self):
        """偵測 P0 是否被觸摸。"""
        return Touch.P0()

    def touchP1(self):
        """偵測 P1 是否被觸摸。"""
        return Touch.P1()

    def touchP2(self):
        """偵測 P2 是否被觸摸。"""
        return Touch.P2()

    def ultrasonic(self, pin_trig, pin_echo):
        if self._hcsr04 is None:
            self._hcsr04 = HCSR04(pin_trig, pin_echo)
        return self._hcsr04.distance_cm()

    def adc(self, pin_num):
        """
        讀取指定 GPIO 腳位的類比電壓值。

        Args:
            pin_num (int): 要讀取類比電壓的 GPIO 腳位號碼。

        Returns:
            int: 類比電壓的取樣值 (0-4095)。
        """
        try:
            adc_pin = ADC(Pin(pin_num))
            adc_pin.atten(ADC.ATTN_11DB)  # 設定最大讀取電壓範圍（約3.3V）
            value = adc_pin.read()
            self.log('DEBUG', f"GPIO{pin_num} 類比電壓值: {value}")
            return value
        except Exception as e:
            self.log('ERROR', f"讀取 GPIO{pin_num} 類比電壓失敗: {e}")
            return None

    def sg90(self, pin_num, angle_degrees):
        """
        使用 SG90 類別控制連接到指定引腳的伺服馬達到特定角度。

        Args:
            pin_num (int): 連接伺服馬達的 GPIO 引腳號碼。
            angle_degrees (int | float): 伺服馬達的目標角度 (通常為 0-180 度)。
        """
        if pin_num not in self._sg90_motors:
            self.log('DEBUG', f"為 GPIO {pin_num} 初始化新的 SG90 馬達物件。")
            try:
                self._sg90_motors[pin_num] = SG90(pin_num)
            except Exception as e:
                self.log('ERROR', f"為 GPIO {pin_num} 初始化 SG90 馬達失敗: {e}")
                return

        motor = self._sg90_motors.get(pin_num)
        if motor:
            self.log('DEBUG', f"設定 GPIO {pin_num} 上的 SG90 至角度 {angle_degrees} 度。")
            try:
                motor.set_angle(angle_degrees)
                #self.log('INFO', f"SG90 在 GPIO {pin_num} 上已移動至 {angle_degrees} 度。")
            except Exception as e:
                self.log('ERROR', f"控制 GPIO {pin_num} 上的 SG90 失敗: {e}")
        else:
            self.log('ERROR', f"無法取得 GPIO {pin_num} 的 SG90 馬達物件。")

    def vibration(self, pin_num, callback, debounce_ms=100):
        if pin_num not in self._vibration_sensors:
            self.log('INFO', f"為 GPIO {pin_num} 初始化新的 _VibrationSensor 物件。")
            try:
                sensor = _VibrationSensor(pinNum=pin_num, callback=callback, DEBOUNCE_MS=debounce_ms)
                self._vibration_sensors[pin_num] = sensor
                self.log('INFO', f"已於 GPIO {pin_num} 設定震動偵測，去抖動時間 {debounce_ms}ms。")
            except Exception as e:
                self.log('ERROR', f"為 GPIO {pin_num} 初始化 _VibrationSensor 失敗: {e}")
                return
        else:
            sensor = self._vibration_sensors[pin_num]
            self.log('INFO', f"重複使用 GPIO {pin_num} 的現有 _VibrationSensor 物件。更新回呼及去抖動時間。")
            sensor.user_callback = callback
            sensor.DEBOUNCE_MS = debounce_ms
            # Reset lastTrigger when parameters are updated to reflect new debounce or callback logic immediately
            if hasattr(sensor, 'lastTrigger'): # Check if _VibrationSensor has lastTrigger (it should based on your code)
                 sensor.lastTrigger = micropython.require("utime").ticks_ms() # Use micropython.require for utime
            self.log('INFO', f"GPIO {pin_num} 的震動偵測已更新，新的去抖動時間 {debounce_ms}ms。")            
            

    def soundDetect(self, pin_num, callback, debounce_ms=500):
        """
        設定指定 GPIO 腳位的聲音偵測。

        Args:
            pin_num (int): 要監聽聲音的 GPIO 腳位號碼。
            callback (function): 偵測到聲音時要執行的回呼函數。
                                 此回呼函數不應接收任何參數。
            debounce_ms (int, optional): 去彈跳時間 (毫秒)。預設為 500。
        """
        if pin_num not in self._sound_sensors:
            self.log('INFO', f"為 GPIO {pin_num} 初始化新的 SoundSensor 物件。")
            try:
                sensor = SoundSensor(pinNum=pin_num, callback=callback, DEBOUNCE_MS=debounce_ms)
                self._sound_sensors[pin_num] = sensor
                self.log('INFO', f"已於 GPIO {pin_num} 設定聲音偵測，去抖動時間 {debounce_ms}ms。")
            except Exception as e:
                self.log('ERROR', f"為 GPIO {pin_num} 初始化 SoundSensor 失敗: {e}")
                return
        else:
            sensor = self._sound_sensors[pin_num]
            self.log('INFO', f"重複使用 GPIO {pin_num} 的現有 SoundSensor 物件。更新回呼及去抖動時間。")
            sensor.user_callback = callback
            sensor.DEBOUNCE_MS = debounce_ms
            # Reset lastTrigger when parameters are updated to reflect new debounce or callback logic immediately
            if hasattr(sensor, 'lastTrigger'): # Check if SoundSensor has lastTrigger (it should based on your code)
                 sensor.lastTrigger = micropython.require("utime").ticks_ms() # Use micropython.require for utime
            self.log('INFO', f"GPIO {pin_num} 的聲音偵測已更新，新的去抖動時間 {debounce_ms}ms。")

    def dht11(self, pin_num):
        """
        讀取指定 GPIO 腳位的 DHT11 傳感器的溫度和濕度。

        Args:
            pin_num (int): 連接 DHT11 傳感器的 GPIO 腳位號碼。

        Returns:
            tuple: 包含 (溫度, 濕度) 的元組。若讀取失敗，則返回 (None, None)。
                   溫度單位為攝氏度 (°C)，濕度單位為百分比 (%)。
        """
        try:
            sensor = DHT11(Pin(pin_num))
            sensor.measure()
            temp = sensor.temperature()
            humi = sensor.humidity()
            #self.log('INFO', f"DHT11 on GPIO {pin_num}: Temp={temp}°C, Humidity={humi}%")
            return temp, humi
        except Exception as e:
            self.log('ERROR', f"Failed to read from DHT11 on GPIO {pin_num}: {e}")
            return None, None

    def setPin(self, pin_num, state):
        """
        指定 GPIO 腳位輸出高電位或低電位。

        Args:
            pin_num (int): 要控制的 GPIO 腳位號碼。
            state (bool): True 代表高電位 (on), False 代表低電位 (off)。
        """
        try:
            pin = machine.Pin(pin_num, machine.Pin.OUT)
            if state:
                pin.on()
            else:
                pin.off()
            #self.log('INFO', f"GPIO {pin_num} 已設定為 {'高電位' if state else '低電位'}。")
        except Exception as e:
            self.log('ERROR', f"設定 GPIO {pin_num} 輸出狀態失敗: {e}")

    def clear(self):
        self.showAll(0, 0, 0)

    def showAll(self, r, g, b):
        r = int(r / 10)
        g = int(g / 10)
        b = int(b / 10)
        for led in range(25):
            self.np[led] = (r, g, b)
        self.np.write()

    def show(*args):
        num_args = len(args)
        self = args[0]
        num = args[1]
        r = args[2]
        g = args[3]
        b = args[4]
        brightness = 1
        if (num_args == 6):
            brightness = args[5]/100.0
        r = int(r / 10 * brightness)
        g = int(g / 10 * brightness)
        b = int(b / 10 * brightness)
        self.np[num] = (r, g, b)
        self.np.write()

    def matrix(self, r, g, b, data):
        data = get_image(data)
        matrix = [[int(data[i*5 + j]) for j in range(5)] for i in range(5)]
        reversed_matrix = [list(reversed(row)) for row in matrix]
        transposed_matrix = [[reversed_matrix[j][i]
                              for j in range(5)] for i in range(5)]
        data = "".join(str(transposed_matrix[i][j])
                       for i in range(5) for j in range(5))
        for i in range(len(data)):
            if data[i] == '0':
                self.show(i, 0, 0, 0)
            elif data[i] == '1':
                self.show(i, r, g, b)

    def draw(self, data):
        self.showAll(0, 0, 0)
        for i in range(0, len(data), 8):
            num = int(data[i:i+2], 16)  # 燈號
            num = self.wled[num]
            hex_color = data[i+2:i+8]  # 顏色
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            self.show(num, r, g, b)

    def sleep(self, i):
        time.sleep(i)

    def scroll(self, r, g, b, scroll_data, delay=0.2):
        r = int(r / 10)
        g = int(g / 10)
        b = int(b / 10)
        # 跑馬燈 5x5 陣列
        scroll_string = ["", "", "", "", ""]
        # 要顯示的資料串再一起
        for i in range(0, 5):
            scroll_string[i] = (
                "".join(get_array(char)[i] for char in scroll_data)
                if type(scroll_data) == str
                else "".join(get_array(image)[i] for image in scroll_data)
            )
        # 至少要刷新 6 次把最後一次螢幕沒刷新的資料清掉
        for _ in range(0, len(scroll_data) * 5 + 1):
            # 資料處理
            data = (
                scroll_string[0][0:5]
                + scroll_string[1][0:5]
                + scroll_string[2][0:5]
                + scroll_string[3][0:5]
                + scroll_string[4][0:5]
            )
            matrix = [[int(data[i * 5 + j]) for j in range(5)]
                      for i in range(5)]
            reversed_matrix = [list(reversed(row)) for row in matrix]
            transposed_matrix = [
                [reversed_matrix[j][i] for j in range(5)] for i in range(5)
            ]
            data = "".join(
                str(transposed_matrix[i][j]) for i in range(5) for j in range(5)
            )
            for i in range(len(data)):
                if data[i] == "0":
                    self.np[i] = (0, 0, 0)
                elif data[i] == "1":
                    self.np[i] = (r, g, b)
            self.np.write()
            # 整個 5x5 陣列往左 shift 1 bit，最後面補 0
            for array_index in range(0, 5):
                scroll_string[array_index] = scroll_string[array_index][1:] + "0"
            self.sleep(delay)
        self.clear()