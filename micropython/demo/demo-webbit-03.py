import uasyncio
import urandom
import utime
from webduino.webbit import WebBit

# 遊戲狀態常數
WELCOME = 0      # 歡迎畫面
SHOWING = 1      # 顯示序列中
WAITING = 2      # 等待玩家輸入
SUCCESS = 3      # 成功回饋
FAIL = 4         # 失敗回饋

class TouchGame:
    def __init__(self, wbit):
        self.wbit = wbit
        self.state = WELCOME
        self.level = 1                # 目前關卡
        self.sequence = []            # 正確的觸控序列
        self.player_input = []        # 玩家輸入序列
        self.current_showing = 0      # 目前顯示到第幾個
        self.last_touch_time = 0      # 最後觸控時間(防彈跳)
        
    def get_sequence_length(self):
        """根據關卡決定序列長度"""
        if self.level == 1:
            return 2
        elif self.level == 2:
            return 3
        elif self.level == 3:
            return 4
        else:
            return 5  # 第4關以上最高難度
    
    def generate_sequence(self):
        """生成隨機觸控序列 (0=P0, 1=P1, 2=P2)"""
        length = self.get_sequence_length()
        self.sequence = []
        for i in range(length):
            # 生成 0-2 的隨機數，對應 P0, P1, P2
            self.sequence.append(urandom.randint(0, 2))
        print(f"第{self.level}關序列: {self.sequence}")  # 除錯用
    
    async def show_welcome(self):
        """顯示歡迎畫面"""
        self.wbit.matrix(100, 100, 0, "happy")  # 黃色開心符號
        await uasyncio.sleep_ms(2000)
        
        # 進入顯示序列狀態
        self.state = SHOWING
        self.generate_sequence()
        self.current_showing = 0
        print(f"開始第{self.level}關")
    
    async def show_sequence(self):
        """依序顯示觸控序列"""
        if self.current_showing < len(self.sequence):
            pin = self.sequence[self.current_showing]
            
            # 根據接點顯示對應顏色
            if pin == 0:  # P0 對應紅色
                self.wbit.showAll(80, 0, 0)
            elif pin == 1:  # P1 對應綠色
                self.wbit.showAll(0, 80, 0)
            elif pin == 2:  # P2 對應藍色
                self.wbit.showAll(0, 0, 80)
            
            await uasyncio.sleep_ms(800)  # 顯示800ms
            self.wbit.showAll(0, 0, 0)    # 關閉所有燈
            await uasyncio.sleep_ms(300)  # 間隔300ms
            
            self.current_showing += 1
        else:
            # 序列顯示完畢，等待玩家輸入
            self.state = WAITING
            self.player_input = []
            print("請按照順序觸碰 P0/P1/P2")
    
    async def check_touch_input(self):
        """檢查觸控輸入並判斷正確性"""
        current_time = utime.ticks_ms()
        
        # 防止重複觸發(去彈跳機制)
        if utime.ticks_diff(current_time, self.last_touch_time) < 300:
            return
        
        # 檢測哪個接點被觸摸
        touched_pin = -1
        if self.wbit.touchP0():
            touched_pin = 0
        elif self.wbit.touchP1():
            touched_pin = 1
        elif self.wbit.touchP2():
            touched_pin = 2
        
        if touched_pin != -1:
            self.last_touch_time = current_time
            self.player_input.append(touched_pin)
            
            # 即時視覺回饋：顯示對應顏色
            if touched_pin == 0:    # P0 紅色
                self.wbit.showAll(80, 0, 0)
            elif touched_pin == 1:  # P1 綠色
                self.wbit.showAll(0, 80, 0)
            elif touched_pin == 2:  # P2 藍色
                self.wbit.showAll(0, 0, 80)
            
            await uasyncio.sleep_ms(200)
            self.wbit.showAll(0, 0, 0)  # 關閉燈光
            
            # 檢查當前輸入是否正確
            current_index = len(self.player_input) - 1
            if self.player_input[current_index] != self.sequence[current_index]:
                # 輸入錯誤，進入失敗狀態
                self.state = FAIL
                print("輸入錯誤！")
                return
            
            # 檢查是否完成整個序列
            if len(self.player_input) == len(self.sequence):
                # 全部輸入正確，進入成功狀態
                self.state = SUCCESS
                print("成功！")
    
    async def show_success(self):
        """顯示成功回饋並進入下一關"""
        self.wbit.matrix(0, 100, 0, "tick")  # 綠色打勾符號
        await uasyncio.sleep_ms(1500)
        
        self.level += 1
        
        # 檢查是否達到特殊里程碑
        if self.level > 10:  # 假設10關為完美通關
            self.wbit.matrix(100, 0, 100, "star")  # 紫色星星符號
            await uasyncio.sleep_ms(3000)
            print("完美通關！遊戲重新開始")
            self.level = 1  # 重新開始
        
        # 進入下一關的顯示序列狀態
        self.state = SHOWING
        self.generate_sequence()
        self.current_showing = 0
    
    async def show_fail(self):
        """顯示失敗回饋並重新開始"""
        self.wbit.matrix(100, 0, 0, "cry")  # 紅色難過符號
        await uasyncio.sleep_ms(2000)
        
        # 重新開始遊戲
        print("遊戲重新開始")
        self.level = 1
        self.state = WELCOME

async def main():
    # 初始化 WebBit (不使用MQTT)
    wbit = WebBit(mqtt=False)
    
    # 創建遊戲實例
    game = TouchGame(wbit)
    
    print("=== WebBit 觸控順序挑戰遊戲 ===")
    print("遊戲規則：")
    print("1. 觀察燈光顯示的順序")
    print("2. P0=紅色, P1=綠色, P2=藍色")
    print("3. 按照相同順序觸碰對應接點")
    print("4. 成功進入下一關，失敗重新開始")
    
    # 主遊戲迴圈
    while True:
        if game.state == WELCOME:
            await game.show_welcome()
        elif game.state == SHOWING:
            await game.show_sequence()
        elif game.state == WAITING:
            await game.check_touch_input()
        elif game.state == SUCCESS:
            await game.show_success()
        elif game.state == FAIL:
            await game.show_fail()
        
        await uasyncio.sleep_ms(10)  # 短暫延遲，避免CPU過載

# 啟動遊戲
uasyncio.run(main())
