from machine import SPI, Pin
from lib import st7735_buf
from lib.easydisplay import EasyDisplay

class Display:
    def __init__(self, font="/text_lite_16px_2312.v3.bmf", width=80, height=160, baudrate=40000000, polarity=0, phase=0,
                 sck_pin=5, mosi_pin=3, cs_pin=4, dc_pin=2, res_pin=1, bl_pin=37,
                 rotate=3, invert=False, rgb=True, color=0xFFFF, clear=True):
        self.spi = SPI(2, baudrate=baudrate, polarity=polarity, phase=phase, sck=Pin(sck_pin), mosi=Pin(mosi_pin))
        self.dp = st7735_buf.ST7735(
            width=width, height=height, spi=self.spi,
            cs=Pin(cs_pin), dc=Pin(dc_pin), res=Pin(res_pin),
            rotate=rotate, bl=Pin(bl_pin), invert=True, rgb=rgb
        )
        self.ed = EasyDisplay(self.dp, "RGB565", font=font, show=True)
        self.color = color
        self.clear_screen = clear
        if clear:
            self.ed.clear()

    def setColor(self, r, b, g):
        # 將 0~100 的範圍轉換到 0~255
        r = int(r * 255 / 100)
        g = int(g * 255 / 100)
        b = int(b * 255 / 100)
        
        # 轉換為 RGB565 格式
        self.color = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    def bmp(self,img,x,y):
        self.ed.bmp(img,x,y)

    def rect(self, x, y, w, h, color):
        self.ed.rect(x, y, w, h, color)
        
    def clear_rect(self,x,y,w,h):
        self.ed.fill_rect(x, y, w, h, 0)
        self.ed.show()

    def fill_rect(self,x,y,w,h,color):
        self.ed.fill_rect(x, y, w, h, color)
        self.ed.show()

    def text(self, text, x, y, color=None, clear=None):
        if color is None:
            color = self.color
        if clear is None:
            clear = self.clear_screen
        self.ed.text(text, x, y, color=color, clear=clear)

    def clear(self):
        self.ed.clear()