import uasyncio
from webduino.webbit import WebBit

# 定義震動發生時的回調函數
def on_vibration():
    print("Vibration detected!")
    # 顯示紅燈
    wbit.showAll(100, 0, 0)
    # 0.5秒後執行恢復綠燈的協程
    uasyncio.create_task(turn_green_after_delay())

# 定義0.5秒後恢復綠燈的協程
async def turn_green_after_delay():
    await uasyncio.sleep_ms(500)
    # 顯示綠燈
    wbit.showAll(0, 100, 0)
    print("Turned green")

async def main():
    global wbit
    wbit = WebBit()

    # 初始顯示綠燈
    wbit.showAll(0, 100, 0)
    print("Initial: Green light")

    # 設定1號腳偵測震動，並指定回調函數
    # debounce_ms 設為 200 毫秒，避免短時間內重複觸發
    wbit.vibration(1, on_vibration, debounce_ms=200)
    print("Vibration sensor on pin 1 initialized.")

    while True:
        # 主循環中可以執行其他任務，或者保持休眠
        # WebBit的震動偵測是在背景執行的
        await uasyncio.sleep_ms(100)

if __name__ == '__main__':
    uasyncio.run(main())
