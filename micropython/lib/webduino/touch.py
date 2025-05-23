from machine import ADC, Pin
import time

class Touch:
    # 可動態支援的 ADC pin 映射
    _pin_map = {
        'p0': 3,  # 物理 Pin3
        'p1': 1,  # 物理 Pin1
        'p2': 2,  # 物理 Pin2
    }
    # 動態管理每路 ADC 實例、讀值緩衝區與觸發狀態
    _adcs = {}
    _buffers = {}
    _active = {}
    # 各通道專屬差異閾值
    _delta_thresholds = {
        'p0': 150,
        'p1': 500,
        'p2': 500,
    }

    @classmethod
    def _init_channel(cls, name):
        """
        第一次呼叫時才初始化特定通道：
        - 建立 ADC
        - 初始化緩衝區
        - 初始化觸發狀態
        """
        if name not in cls._pin_map:
            raise ValueError(f"Unknown channel: {name}")
        if name not in cls._adcs:
            adc = ADC(Pin(cls._pin_map[name]))
            adc.atten(ADC.ATTN_11DB)
            cls._adcs[name] = adc
            cls._buffers[name] = []
            cls._active[name] = False

    @classmethod
    def _touched(cls, name):
        """
        通用觸摸偵測邏輯：
        1. 動態初始化通道
        2. 切換 ADC 通道後讀兩次 (丟棄第一次)
        3. 將第二次讀值加入緩衝區
        4. 計算最後三筆讀值差異並做去抖
        """
        cls._init_channel(name)
        adc = cls._adcs[name]
        buf = cls._buffers[name]
        threshold = cls._delta_thresholds.get(name, 500)

        # 切換通道後，先丟棄一次不穩定讀取
        time.sleep_ms(10)
        adc.read()
        # 取得有效值
        val = adc.read()

        # 更新緩衝區
        buf.append(val)
        if len(buf) > 3:
            buf.pop(0)
        # 尚未累積三筆前，不判定觸發
        if len(buf) < 3:
            return False

        # 計算最後兩筆平均與最舊值差
        avg_last_two = (buf[-1] + buf[-2]) / 2
        diff = avg_last_two - buf[-3]

        # 根據狀態與閾值，決定是否回傳一次觸發
        triggered = False
        if not cls._active[name] and diff > threshold:
            triggered = True
            cls._active[name] = True
        elif cls._active[name] and diff <= threshold:
            cls._active[name] = False

        return triggered

    @classmethod
    def P0(cls):
        return cls._touched('p0')

    @classmethod
    def P1(cls):
        return cls._touched('p1')

    @classmethod
    def P2(cls):
        return cls._touched('p2')

# 範例使用：
# while True:
#     if Touch.P0(): print("▶ P0 被觸摸！")
#     if Touch.P1(): print("▶ P1 被觸摸！")
#     if Touch.P2(): print("▶ P2 被觸摸！")
#     time.sleep(0.1)
