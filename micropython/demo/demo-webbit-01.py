import uasyncio
from webduino.webbit import WebBit

async def main():
    wbit = WebBit()

    while True:
        if wbit.btnA() and wbit.btnB():
            # 按下 A+B，顯示紅色
            wbit.showAll(100, 0, 0)
        elif wbit.btnA():
            # 按下 A，顯示藍色
            wbit.showAll(0, 0, 100)
        elif wbit.btnB():
            # 按下 B，顯示綠色
            wbit.showAll(0, 100, 0)
        else:
            # 沒有按鈕按下，熄滅所有燈
            wbit.showAll(0, 0, 0)
        
        await uasyncio.sleep_ms(10)

uasyncio.run(main())
