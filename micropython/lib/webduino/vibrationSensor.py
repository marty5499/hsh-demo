import machine, utime, micropython

class _VibrationSensor:
    def __init__(self, pinNum, callback=None, DEBOUNCE_MS=100):
        self.pinNum = pinNum
        self.DEBOUNCE_MS = DEBOUNCE_MS
        self.user_callback = callback
        self.lastTrigger= utime.ticks_ms()
        try:
            self.pin = machine.Pin(self.pinNum, machine.Pin.IN, machine.Pin.PULL_UP)
            self.pin.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=self._irq_handler_wrapper)
        except Exception as e:
            print(f"SoundSensor 錯誤：初始化時無法設定 Pin {self.pinNum} 的中斷: {e}")
            raise

    def _irq_handler_wrapper(self, pin_obj):
        try:
            micropython.schedule(self._process_scheduled_trigger, pin_obj)
        except RuntimeError as e: # 捕捉 schedule queue full 的情況
            pass

    def _process_scheduled_trigger(self, scheduled_pin_obj):
        if utime.ticks_ms()-self.lastTrigger < self.DEBOUNCE_MS: return
        if self.user_callback:
            try:
                self.user_callback()
                self.lastTrigger = utime.ticks_ms()
            except Exception as e:
                print(f"SoundSensor 使用者回呼函式錯誤: {e}")