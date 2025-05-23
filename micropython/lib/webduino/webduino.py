import network, time, machine, ubinascii, os
from machine import Pin, PWM, Timer, WDT
from umqtt.simple import MQTTClient
from WebServer import WebServer
import Config

class debug:
    state = True
    def on():
        debug.state = True
    def off():
        debug.state = False
    def print(msg="",msg2="",msg3=""):
        if debug.state:
            print(msg,msg2)        

class WiFi:
    onlineCallback = None
    ssid="webduino.io"
    pwd="webduino"
    ip="unknown"
    
    def disconnect():
        WiFi.sta.disconnect()

    def check():
        print(WiFi.sta.isconnected())

    def onlilne(cb):
        WiFi.onlineCallback = cb

    def startKeepConnect():
        WiFi.timer = Timer(0)
        WiFi.timer.init(period=3000, mode=Timer.PERIODIC, callback=WiFi.checkConnection)
    
    def checkConnection(t):
        if not WiFi.sta.isconnected():
            WiFi.connect(WiFi.ssid,WiFi.pwd)
            debug.print("!!!! online callback... !!!!")
        return WiFi.sta.isconnected()

    def enableAP(ssid="myboard",pwd="12345678"):
        WiFi.ap = network.WLAN(network.AP_IF)
        WiFi.ap.active(True)
        WiFi.ap.config(essid=ssid,password=pwd)

    def connect(ssid="webduino.io",pwd="webduino"):
        WiFi.ssid = ssid
        WiFi.pwd = pwd
        WiFi.sta = sta_if = network.WLAN(network.STA_IF)
        sta_if.active(True)
        sta_if.disconnect()
        debug.print('connecting to network...',WiFi.ssid)
        if(not sta_if.isconnected()):
            sta_if.connect(ssid,pwd)
        if(WiFi.onlineCallback is not None):
            WiFi.onlineCallback(False)
        if not sta_if.isconnected():
            try:
                sta_if.connect(ssid,pwd)
            except:
                debug.print("connect...")
        cnt = 0
        while not sta_if.isconnected():
            cnt = cnt + 1
            time.sleep(0.5)
            if cnt == 10:
                cnt = 0
                debug.print("retry connect...")
        WiFi.ip = WiFi.sta.ifconfig()[0];
        if(WiFi.onlineCallback is not None):
            WiFi.onlineCallback(True)
        WiFi.startKeepConnect()
        return True


class MQTT:
    
    def connect(server = 'mqtt1.webduino.io',user ='webduino' ,pwd='webduino'):
        MQTT.server = server
        MQTT.user = user
        MQTT.pwd = pwd
        mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode().replace(':','')
        MQTT.client = MQTTClient('wa'+mac, server, user=user, password=pwd)
        state = True if MQTT.client.connect() == 0 else False
        try:
            debug.print("resubscribe:",MQTT.subTopic)
            MQTT.sub(MQTT.subTopic,MQTT.callback)
        except:
            pass
        return state
        
    def pub(topic,msg):
        MQTT.client.publish(topic,msg)

    def sub(topic,cb):
        MQTT.subTopic = topic
        MQTT.callback = cb
        MQTT.client.set_callback(cb)
        MQTT.client.subscribe(topic)

    def checkMsg():
        try:
            MQTT.client.check_msg()
        except:
            pass

class Board:
    
    Ver = '0.1.9b'
    def __init__(self,devId=''):
        self.wifi = WiFi
        self.mqtt = MQTT
        self.wifi.onlilne(self.online)
        self.topics = {}
        self.topic_report = 'waboard/state'
        self.config = Config
        self.now = 0
        json = self.config.load()
        #print("json:",json)
        if(devId == ''):
            if json['devId']=='unknown':
                json['devId'] = self.mac().replace(':','')
            devId = json['devId']
        else:
            json['devId'] = devId
        self.config.save()
        self.devId = devId
        self.devPasswd = json['devPasswd']
        self.topic_cmd = self.devId+'/cmd'
        self.enableAP()
        self.connect(ssid=json['ssid1'],pwd=json['passwd1'])
        debug.print('board IP:'+self.ip())

    def ap(self):
        return self.wifi.ssid

    def ip(self):
        return self.wifi.ip

    def mac(self):
        return ubinascii.hexlify(network.WLAN().config('mac'),':').decode()

    def enableAP(self):
        ssid = self.config.data['devSSID']
        pwd = self.config.data['devPasswd']
        self.wifi.enableAP(ssid,pwd)
        self.wifi.web = WebServer(self,80)
        self.wifi.web.listener()
        debug.print("webServer start...")
        
    def online(self,status):
        if status:
            self.mqtt.connect()
            debug.print("connect mqtt...OK")
        else:
            debug.print("offline...")
            pass
        
    def connect(self,ssid='webduino.io',pwd='webduino'):
        while True:
            if self.wifi.connect(ssid,pwd):
                break
        debug.print("WiFi Ready , MQTT Ready , ready to go...")
        self.onMsg(self.topic_cmd,self.execCmd)
        self.report('boot')
        return self
        
    def onMsg(self,topic,cbFunc):
        self.topics[topic] = cbFunc
        self.mqtt.sub(topic,self.dispatch)
        
    def dispatch(self,topic,msg):
        topic = topic.decode("utf-8")
        msg = msg.decode("utf-8")
        self.topics[topic](msg)
    
    def publish(self,topic,msg):
        self.mqtt.pub(topic,msg);

    def loop(self):
        debug.print("run...")
        while True:
            self.check()
            time.sleep(0.1)

    def check(self):
        self.mqtt.checkMsg()
        self.now = self.now + 1
        if self.now % 300 == 0:
            #print("mqtt ping...")
            try:
                self.mqtt.client.ping()
            except:
                #print("mqtt broken!")
                pass
        if self.now % 600 == 0:
            print("wifi check...",self.wifi.checkConnection(self.now))
            self.now = 0        
        
    def ping(self):
        self.mqtt.client.ping()

    def report(self,cmd):
        report = cmd + ' '+self.devId
        self.mqtt.pub(self.topic_report,report)
    
    def execCmd(self,data):
        dataArgs = data.split(' ')
        print("exceCmd:",dataArgs)
        cmd = dataArgs[0]
        if cmd == 'reboot':
            self.report('reboot')
            time.sleep(1)
            machine.reset()
        elif cmd == 'reset':
            os.remove('main.py')
            self.report('reset')
            time.sleep(1)
            machine.reset()
        elif cmd == 'save':
            url = dataArgs[1]
            file = dataArgs[2]
            f = open('cmd.py','w')
            f.write('import os,machine\r\n')
            f.write('os.remove("cmd.py")\r\n')
            f.write('from utils import *\r\n')
            f.write('from webduino import Board\r\n')
            f.write('Board()\r\n')
            f.write("Utils.save('"+url+"','"+file+"')\r\n")
            f.close()
            self.report('save')
            time.sleep(1)
            machine.reset()