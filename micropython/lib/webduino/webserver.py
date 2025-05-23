import socket
import time
import machine,gc,json
from webduino.debug import debug

class WebServer:  
    
    def __init__(self, board, cam_app=None, port=80):
        self.addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
        self.ss = socket.socket()
        self.ss.bind(self.addr)
        self.ss.listen(1)
        self.board = board
        self.cam_app = cam_app  # 將 cam_app 作為屬性存儲

    def unquote(self, string):
        _hextobyte_cache = None
        if not string:
            return b''
        if isinstance(string, str):
            string = string.encode('utf-8')
        bits = string.split(b'%')
        if len(bits) == 1:
            return string
        res = [bits[0]]
        append = res.append
        if _hextobyte_cache is None:
            _hextobyte_cache = {}
        for item in bits[1:]:
            try:
                code = item[:2]
                char = _hextobyte_cache.get(code)
                if char is None:
                    char = _hextobyte_cache[code] = bytes([int(code, 16)])
                append(char)
                append(item[2:])
            except KeyError:
                append(b'%')
                append(item)
        return b''.join(res)
 
    def processPost(self, cs, req):
        cs.send(b'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl_file = req['stream']
        contentLen = req['Content-Length']
        urlPage = req['url'][1]
        formData = cl_file.read(contentLen)
        if urlPage == '/save':
            config = self.unquote(formData).decode("utf-8")[7:]
            debug.print("save config:"+config)
            self.board.config.updateFromString(config)
            self.board.config.save()
            cs.send(b"完成儲存，開發板將自動連上wifi")
            cs.close()
            debug.print("Restart...")
            time.sleep(3)
            machine.reset()
        cs.close() 

    def processGet(self, cs, req):
        url = req.get('url', ['', '/'])[1]
        if url == '/signal':
            try:
                rssi = self.board.wifi.sta.status('rssi')
                response = {'RSSI': rssi}
                self.sendJSON(cs, response)
                return
            except Exception as e:
                debug.print("Error getting RSSI:", e)
                self.sendJSON(cs, {'error': 'Failed to get RSSI'})
                return

        debug.print("processGet")
        try:
            filename = req['url'][1][1:]
            if filename == 'favicon.ico':
                cs.sendall(b'HTTP/1.0 204 No Content\r\n')
                cs.sendall(b'Content-Length: 0\r\n')
                cs.sendall(b'Cache-Control: public, max-age=31536000\r\n\r\n')
                cs.close()
                return
            if filename == '':
                filename = 'index.html'
            if filename == 'value.js':
                cs.sendall(b'HTTP/1.0 200 OK\r\nContent-type: application/javascript\r\n\r\n')
                config = self.board.config.data
                config['AP'] = self.board.ap()
                config['IP'] = self.board.ip()
                config['MAC'] = self.board.mac()
                config['Ver'] = self.board.Ver
                cs.sendall(("var data=" + str(config)).encode('utf-8'))
            elif filename == 'image':
                self.processImage(cs)
            elif filename == 'stream':
                self.processStream(cs)
            else:
                cs.sendall(b'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                with open(filename, "r") as file:
                    while True:
                        line = file.readline()
                        if not line:
                            break
                        cs.sendall(line.encode('utf-8'))
        except Exception as e:
            debug.print("Error: "+filename)
            debug.print(e)
        cs.close()

    def processImage(self, cs):
        img = self.cam.capture()  # Capture image from camera
        cs.sendall(b'HTTP/1.0 200 OK\r\nContent-Type: image/jpeg\r\nAccess-Control-Allow-Origin: *\r\n\r\n')
        cs.sendall(img)  # Send image binary data
        cs.close()
        gc.collect()

    def processStream(self, cs):
        #cs.sendall(b'HTTP/1.0 200 OK\r\nContent-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n')
        cs.sendall(b'HTTP/1.0 200 OK\r\n')
        cs.sendall(b'Content-Type: multipart/x-mixed-replace; boundary=frame\r\n')
        cs.sendall(b'Access-Control-Allow-Origin: *\r\n\r\n')  # 添加這一行來設置CORS標頭

        try:
            while True:
                img = self.cam.capture()
                cs.sendall(b'--frame\r\n')
                cs.sendall(b'Content-Type: image/jpeg\r\n\r\n')
                cs.sendall(img)
                cs.sendall(b'\r\n')
                gc.collect()
                time.sleep(0.1)  # Adjust the delay as needed
        except Exception as e:
            debug.print("Streaming error:", e)
        cs.close()

    def acceptSocket(self, sc):
        cs, addr = self.ss.accept()
        req = {}
        contentLen = None
        cl_file = cs.makefile('rwb', 0)
        req['stream'] = cl_file
        while True: 
            line = cl_file.readline().decode("utf-8")
            if not line or line == '\r\n':
                break 
            if 'Content-Length:' in line:
                req['Content-Length'] = int(line.split(':')[1].strip())
            if 'GET /' in line or 'POST /' in line:
                req['url'] = line.split(' ')
        if(len(req.get('url', []))==0):
            pass
            debug.print("empty req , close socket")
            cs.close()
        elif req.get('url', [])[0] == "POST":
            self.processPost(cs, req)
        elif req.get('url', [])[0] == "GET":
            self.processGet(cs, req)        

    def listener(self):
        self.ss.setsockopt(socket.SOL_SOCKET, 20, self.acceptSocket)

    def sendJSON(self, cs, data):
        """發送 JSON 格式的響應"""
        json_str = json.dumps(data)
        response = (
            b'HTTP/1.0 200 OK\r\n'
            b'Content-Type: application/json\r\n'
            b'Access-Control-Allow-Origin: *\r\n'
            b'Content-Length: %d\r\n'
            b'\r\n'
            b'%s' % (len(json_str), json_str.encode('utf-8'))
        )
        cs.sendall(response)
        cs.close()