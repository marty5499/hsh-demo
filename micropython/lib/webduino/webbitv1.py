import machine,neopixel,time,dht,math
from machine import ADC, I2C, Pin
from webduino.board import Board
from webduino.debug import debug
from webduino.image import get_image

class Temp():
    def __init__(self):
        self.voltagePower = 3.3
        self.Rs = 10000   # 更改 Rs 的值，根據您的熱敏電阻的規格表
        self.B = 3950
        self.T0 = 273.15
        self.R1 = 2500   # 更改 R1 的值，根據傳感器上的參考電阻的規格表
        self.__temp__ = ADC(Pin(34))  # 溫度傳感器
        self.__temp__.atten(ADC.ATTN_11DB)
        self.lastTemp = 0

    def read(self):
        self.voltageValue = (self.__temp__.read() / 4095) * self.voltagePower
        self.Rt = ((self.voltagePower - self.voltageValue)
                   * self.Rs) / self.voltageValue
        try:
            T = 1 / ((1 / self.T0) + (1 / self.B) *
                     math.log(self.Rt*2 / self.R1))
            self.lastTemp = T - self.T0 + 67
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
        pin17 = machine.PWM(machine.Pin(25), freq=freq, duty=512)
        if (duration >= 10):
            duration = duration/1000.0
        time.sleep(duration)
        machine.PWM(machine.Pin(25), duty=0)

    def playList(self, lst):
        self.queue.extend(lst)

    def stop(self):
        self.queue = []

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
        elif len(args) == 2 and isinstance(args[0], int) and isinstance(args[1], (int, float)):
            # Input: freq, delay
            # print('2')
            self.queue.append([args[0], args[1]])
        self.run()


class WebBit:

    def close(self):
        pass

    def disconnect(self):
        pass

    def __init__(self):
        self.np = neopixel.NeoPixel(machine.Pin(4), 25)
        self.buzzer = Buzzer()
        self.a = Btn(35)
        self.b = Btn(27)
        self.lL = ADC(Pin(36))
        self.rL = ADC(Pin(39))
        self.p1_adc = ADC(Pin(32))
        self.p1_adc.atten(ADC.ATTN_6DB)
        self.lL.atten(ADC.ATTN_11DB)
        self.rL.atten(ADC.ATTN_11DB)
        self._temp = Temp()
        self.showAll(0, 0, 0)
        self.beep()
        self.debug = debug
        self.wled = {0: 20, 1: 15, 2: 10, 3: 5, 4: 0, 5: 21, 6: 16, 7: 11, 8: 6, 9: 1, 10: 22, 11: 17,
                     12: 12, 13: 7, 14: 2, 15: 23, 16: 18, 17: 13, 18: 8, 19: 3, 20: 24, 21: 19, 22: 14, 23: 9, 24: 4}
        self.online = False
        self.pinMap = {'0': 25, '1': 32, '2': 33, '3': 13, '4': 15, '5': 35, '6': 12, '7': 14,
                       '8': 16, '9': 17, '10': 26, '11': 27, '12': 2, '13': 18, '14': 19, '15': 23, '16': 5}
        self.d11 = False

    def get_image(self,image):
        return get_image(image)

    def adc(self):
        return self.p1_adc.read()

    def readPin(self, pinNum):
        return Pin(self.pinMap[str(pinNum)], Pin.IN).value()

    def setPin(self, pinNum, val):
        return Pin(self.pinMap[str(pinNum)], Pin.OUT).value(val)

    def readDHT11_temp(self, pinNum):
        if (not self.d11):
            pin = machine.Pin(self.pinMap[str(pinNum)])
            self.d11 = dht.DHT11(pin)
            self.measureDHT11(pinNum)
        return self.d11.temperature()

    def measureDHT11(self, pinNum):
        if (pinNum == 1):
            raise ValueError("Pin 1 is not supported")
        while True:
            try:
                self.d11.measure()
                return
                time.sleep(1)
            except Exception as e:
                pass  # print(e)

    def readDHT11_humi(self, pinNum):
        if (not self.d11):
            pin = machine.Pin(self.pinMap[str(pinNum)])
            self.d11 = dht.DHT11(pin)
        self.measureDHT11(pinNum)
        return self.d11.humidity()
        
    def sub(self, topic, cb):
        self.connect()
        self.board.onTopic(topic, cb)

    def pub(self, topic, msg, reatain=False):
        self.connect()
        self.board.pub(topic, msg, retain)

    def onTopic(self,topic,cbFunc):
        self.board.topics[topic] = cbFunc        

    def connect(self):
        if self.online == True:
            return
        self.showAll(20, 0, 0)
        try:
            self.board = Board(devId='bitv2')
        except:
            machine.reset()
        self.showAll(0, 0, 0)
        self.online = True

    def checkMsg(self):
        self.connect()
        self.board.mqtt.checkMsg()

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
