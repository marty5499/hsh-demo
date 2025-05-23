import uasyncio
from webduino.webbit import WebBit

sound_detected_flag = False

def sound_detected_callback():
    global sound_detected_flag
    sound_detected_flag = True
    print("Sound Detected!")

async def main():
    wbit = WebBit()
    
    # 初始設定為綠燈
    wbit.showAll(0, 100, 0) # R, G, B (0-100)

    # 設定1號腳偵測聲音，並指定回呼函數
    # pin_num=1 代表使用1號腳位
    wbit.soundDetect(pin_num=1, callback=sound_detected_callback)

    while True:
        global sound_detected_flag
        if sound_detected_flag:
            # 偵測到聲音，顯示紅燈
            wbit.showAll(100, 0, 0)
            await uasyncio.sleep_ms(500) # 等待 0.5 秒
            # 轉回綠燈
            wbit.showAll(0, 100, 0)
            sound_detected_flag = False # 重置旗標
        
        await uasyncio.sleep_ms(10) # 短暫延遲，避免過度占用CPU

if __name__ == '__main__':
    try:
        uasyncio.run(main())
    except KeyboardInterrupt:
        print('stopped')
