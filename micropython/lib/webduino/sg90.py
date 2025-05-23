import machine
import time

class SG90:
    def __init__(self, pin_num, freq=50,
                 min_pulse=0.5, max_pulse=2.5,
                 calibration_offset=0.0):
        """
        SG90 伺服馬達控制器。

        Args:
            pin_num (int): 連接伺服馬達的 GPIO 引腳號碼。
            freq (int): PWM 頻率，預設 50Hz。
            min_pulse (float): 0° 對應的最小脈衝寬度 (ms)。
            max_pulse (float): 180° 對應的最大脈衝寬度 (ms)。
            calibration_offset (float): 校正偏移 (ms)，可微調零點。
        """
        self.pin_num = pin_num
        self.freq = freq
        self.min_pulse = min_pulse
        self.max_pulse = max_pulse
        self.calibration_offset = calibration_offset
        # 初始化 PWM
        self.pwm = machine.PWM(machine.Pin(self.pin_num), freq=self.freq)
        self.log('DEBUG', f"Initialized PWM on pin {self.pin_num} at {self.freq}Hz")

    def log(self, level, msg):
        # 簡單範例：請依實際框架實作
        print(f"[{level}] {msg}")

    def set_angle(self, angle_degrees):
        """
        將伺服馬達移動到指定角度。

        Args:
            angle_degrees (int | float): 目標角度 (0–180°)。
        Returns:
            bool: 操作是否成功。
        """
        # 範圍檢查與限制
        if not (0 <= angle_degrees <= 180):
            original = angle_degrees
            angle_degrees = max(0, min(180, angle_degrees))
            self.log('DEBUG', f"Angle {original}° out of range, clamped to {angle_degrees}°.")

        # 計算脈衝寬度 (ms)
        pulse_span = self.max_pulse - self.min_pulse
        pulse_width_ms = self.min_pulse + (pulse_span * (angle_degrees / 180.0))
        pulse_width_ms += self.calibration_offset

        # 計算 10-bit 占空比 (0–1023)
        period_ms = 1000 / self.freq  # e.g., 50Hz -> 20ms
        duty_val = int((pulse_width_ms / period_ms) * 1023)

        #self.log('DEBUG', f"Set angle {angle_degrees}° -> pulse {pulse_width_ms:.2f}ms -> duty {duty_val}")
        try:
            self.pwm.duty(duty_val)
            # 非阻塞延遲，可改用 time.ticks_ms 進階實作
            time.sleep_ms(100)
            #self.log('INFO', f"Servo moved to {angle_degrees}° on pin {self.pin_num}.")
            return True
        except Exception as e:
            self.log('ERROR', f"Failed to set angle: {e}")
            return False

    def deinit(self):
        """
        結束 PWM，釋放資源。
        """
        self.pwm.deinit()
        self.log('DEBUG', f"Deinitialized PWM on pin {self.pin_num}.")