import uasyncio
from webduino.webbit import WebBit
import time

async def main():
    # 如果需要使用 mqtt , mqtt 要設定 True
    wbit = WebBit(mqtt=False)

    while True:
        # 讀取 pin 1 的溫濕度
        temperature, humidity = wbit.dht11(1)

        if temperature is not None and humidity is not None:
            print(f"溫度: {temperature}°C, 濕度: {humidity}%")
        else:
            print("讀取溫濕度失敗")

        # 每隔2秒讀取一次
        await uasyncio.sleep_ms(2000)

uasyncio.run(main())
