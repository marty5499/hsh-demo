import uasyncio
from webduino.webbit import WebBit
import time

async def main():
    wbit = WebBit()
    trig_pin = 1
    echo_pin = 2

    while True:
        distance = wbit.ultrasonic(trig_pin, echo_pin)
        if distance is not None:
            print(f"距離: {distance} cm")
        else:
            print("讀取超音波感測器失敗")
        await uasyncio.sleep_ms(500) # 每0.5秒讀取一次

uasyncio.run(main())
