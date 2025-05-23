import uasyncio
from webduino.webbit import WebBit

async def main():
    wbit = WebBit()
    pin_analog_in = 1
    pin_servo_out = 9

    while True:
        # 讀取 pin 1 的類比數值 (0-8192)
        analog_value = wbit.adc(pin_analog_in)

        # 將類比數值從 0-8192 等比例轉換到 0-180
        # 轉換公式: servo_angle = (analog_value / 8192) * 180
        servo_angle = int((analog_value / 8192) * 180)

        # 確保角度在 0 到 180 之間
        servo_angle = max(0, min(180, servo_angle))

        # 控制 pin 9 的伺服馬達轉動
        wbit.sg90(pin_servo_out, servo_angle)

        # 打印出目前讀取的類比值和轉換後的角度，方便觀察
        print(f"Analog Value: {analog_value}, Servo Angle: {servo_angle}")

        await uasyncio.sleep_ms(50) # 每50毫秒更新一次

uasyncio.run(main())
