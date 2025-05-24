import uasyncio
from webduino.webbit import WebBit

async def main():
    # 不需要使用 mqtt，所以設定為 False
    wbit = WebBit(mqtt=False)
    
    # 初始化變數
    min_light = 10      # 最低光度閾值
    max_light = 1000    # 最高光度閾值
    min_brightness = 5  # 最低亮度
    max_brightness = 100 # 最高亮度
    
    while True:
        # 讀取左右兩邊的光度值
        left_light_val = wbit.leftLight()
        right_light_val = wbit.rightLight()
        
        # 計算平均光度
        avg_light = (left_light_val + right_light_val) / 2
        
        # 將光度值限制在合理範圍內
        if avg_light < min_light:
            avg_light = min_light
        elif avg_light > max_light:
            avg_light = max_light
        
        # 將光度反向映射到亮度值 (光度越暗，亮度越高)
        # 使用線性映射公式
        brightness = max_brightness - ((avg_light - min_light) / (max_light - min_light)) * (max_brightness - min_brightness)
        brightness = int(brightness)
        
        # 確保亮度值在有效範圍內
        if brightness < min_brightness:
            brightness = min_brightness
        elif brightness > max_brightness:
            brightness = max_brightness
        
        # 設定全屏亮度（白光）
        wbit.showAll(brightness, brightness, brightness)
        
        # 延遲 100 毫秒再次檢測，避免過於頻繁更新
        await uasyncio.sleep_ms(100)

uasyncio.run(main())
