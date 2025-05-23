import uasyncio
from webduino.webbit import WebBit

async def main():
    wbit = WebBit()

    while True:
        analog_value = wbit.adc(1)  # 讀取 Pin1 的類比值
        # 將 0-8192 的數值等比例轉換到 0-100
        brightness = int((analog_value / 8192) * 100)
        
        # 確保亮度值在 0-100 之間
        brightness = max(0, min(100, brightness))
        
        wbit.showAll(brightness, 0, 0)  # 設定所有LED的紅色亮度
        
        await uasyncio.sleep_ms(50) # 短暫延遲

uasyncio.run(main())
