class debug:
    state = False
    level = 4

    def on():
        debug.state = True

    def off():
        debug.state = False

    def print(msg="",msg2="",msg3=""):
        if debug.state:
            print(msg,msg2) 

    def DEBUG(msg):
        if debug.level>=4 : print(f"[DEBUG] {msg}")

    def INFO(msg):
        if debug.level>=3 : print(f"[INFO] {msg}")

    def WARN(msg):
        if debug.level>=2 : print(f"[WARN] {msg}")

    def ERROR(msg):
        if debug.level>=1 : print(f"[ERROR] {msg}")