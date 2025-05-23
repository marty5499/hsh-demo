import network, ubinascii, machine, uasyncio, time
from umqtt.robust import MQTTClient
from webduino.debug import debug

class MQTT:
    _callbacks = {}
    _sub_queue = []  # 新增訂閱資料隊列
    _pub_queue = []  # 新增發布資料隊列
    wdt = None  # 初始化 wdt 屬性為 None
    last_callback_log_time = None # 記錄上次 callback log 的時間點

    @staticmethod
    def connect(user='webduino', pwd='webduino'):
        MQTT.now = 0
        MQTT.user = user
        MQTT.pwd = pwd
        MQTT.keepalive = 60
        mac = ubinascii.hexlify(network.WLAN().config('mac'), ':').decode().replace(':', '')
        MQTT.client = MQTTClient('wa'+mac, MQTT.server, user=user, password=pwd, keepalive=MQTT.keepalive)
        MQTT.set_last_will(MQTT.topic_report, MQTT.topic_report_msg)
        try:
            MQTT.client.connect()
            state = True
        except Exception as e:
            debug.DEBUG("Error connecting using robust client: " + str(e))
            machine.reset()

    @staticmethod
    def pub(topic, msg, retain=False):
        try:
            MQTT.client.publish(topic, msg, retain=retain, qos=0)
            #MQTT._pub_queue.append((topic, msg, retain))
            debug.DEBUG(f"out >>>>>>>>>>>>>>> queued {topic}:{msg} [{len(MQTT._pub_queue)}]")
        except Exception as e:
            debug.DEBUG(f"Queueing publish error: {str(e)}")
            # 考慮是否在此處重置，或讓 checkMsg 中的發布失敗處理
            # machine.reset()

    @staticmethod
    async def process_sub_msg():
        # Process only one message from the queue per call
        if len(MQTT._sub_queue) > 0:
            if MQTT.wdt: MQTT.wdt.feed()
            topic, msg, retain = MQTT._sub_queue.pop(0)
            try:
                start_ticks = time.ticks_ms() # Record start time
                debug.DEBUG(f"in <<< [{len(MQTT._sub_queue)}] processing {topic}:{msg}")
                MQTT._callbacks[topic](topic, msg)
                end_ticks = time.ticks_ms() # Record end time
                duration = time.ticks_diff(end_ticks, start_ticks)
                debug.DEBUG(f"in <<< callback for {topic} took {duration} ms")
                MQTT.last_callback_log_time = time.ticks_ms() # 記錄 callback log 的時間

            except Exception as e:
                debug.DEBUG(f"Error processing message for topic {topic}: {str(e)}")
                machine.reset()

    @staticmethod
    def _safe_callback(topic, msg):
        MQTT._sub_queue.append( (topic.decode('utf-8'), msg, False) )  # 將參數加入隊列

    @staticmethod
    def sub(topic, cb):
        topic_str = topic if isinstance(topic, str) else topic.decode('utf-8')
        if topic_str not in MQTT._callbacks:
            try:
                if not MQTT._callbacks:
                    MQTT.client.set_callback(MQTT._safe_callback)
                MQTT.client.subscribe(topic, qos=0)
                debug.DEBUG(f"Subscribed to topic: {topic_str}")
            except Exception as e:
                debug.DEBUG(f"Subscribe error: {str(e)}")
                machine.reset()
        MQTT._callbacks[topic_str] = cb

    @staticmethod
    def set_last_will(topic, msg, retain=True, qos=0):
        try:
            MQTT.client.set_last_will(topic, msg, retain, qos=0)
        except Exception as e:
            debug.DEBUG(f"Set last will error: {str(e)}")
            machine.reset()

    async def flush_pub_queue(): pass

    @staticmethod
    async def checkMsg():
        try:
            MQTT.client.check_msg()
            await MQTT.process_sub_msg()
            MQTT.now += 1
            if MQTT.now > 300: # rough 30 sec, (keepalive/2) / 0.1s interval
                MQTT.now = 0
                MQTT.client.ping() # 回報 keep_alive
                #debug.DEBUG(f"feed...{int(time.ticks_ms()/1000)}")

        except Exception as e:
            debug.DEBUG(f"MQTT broken: {str(e)}")
            machine.reset()