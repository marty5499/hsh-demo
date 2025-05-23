import usocket as soc
import _thread as th
import time
import gc
import esp
import camera


class webstream:
    
    def start(camera):
        webstream.init(camera)
        webstream.pic = webstream.frame_gen()
        webstream.ss = webstream.serverSocket()
        th.start_new_thread(webstream.srv, (1,))
        #th.start_new_thread(webstream.srv, (2,))

    def init(camera):
        webstream.camera = camera
        webstream.hdr = {
        # start page for streaming 
        # URL: /apikey/webcam
        'live': """HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8

<html>
<head>
<title>Web Camera</title>
</head>
<body>
  <center>
    <h1>Web Camera</h1>
    <img src="/apikey/live" width=640 height=480 />
  </center>
</body>
</html>

        """,
          # live stream -
          # URL: /apikey/live
          'stream': """HTTP/1.1 200 OK\r
Content-Type: multipart/x-mixed-replace; boundary=frame\r
Connection: keep-alive\r
Cache-Control: no-cache, no-store, max-age=0, must-revalidate\r
Expires: Thu, Jan 01 1970 00:00:00 GMT\r
Pragma: no-cache\r\n\r\n""",
          # live stream -
          # URL: 
          'frame': """--frame\r
Content-Type: image/jpeg\r\n\r\n""",
          # still picture - 
          # URL: /apikey/snap
          'snap': """HTTP/1.1 200 OK\r
Content-Type: image/jpeg\r
Content-Length:""",
          # no content error
          # URL: all the rest
          'none': """HTTP/1.1 204 No Content\r
Content-Type: text/plain; charset=utf-8\r
\r
Nothing here!
""",
          # bad request error
          # URL: /favicon.ico
          'favicon': """HTTP/1.1 404\r
\r
""",
          # bad request error
          # URL: all the rest
          'err': """HTTP/1.1 400 Bad Request
Content-Type: text/plain; charset=utf-8\r
\r
Hello? Can not compile
""",
          # OK
          # URL: all the rest
          'OK': """HTTP/1.1 200 OK\r
Content-Type: text/plain; charset=utf-8\r
\r
OK!
"""
        }

    def clean_up(cs):
       cs.close() # flash buffer and close socket
       del cs
       gc.collect()

    def serverSocket():
       # port 80 server - streaming server
       s = soc.socket(soc.AF_INET, soc.SOCK_STREAM)
       s.setsockopt(soc.SOL_SOCKET, soc.SO_REUSEADDR, 1)
       s.bind(('', 8080))
       s.listen(1)  # queue at most 2 clients
       return s
    
    def frame_gen():
        while True:
            #print("framegen()")
            buf = webstream.camera.capture()
            #print("framegen() yield")
            yield buf
            #print("framegen() del")
            del buf
            gc.collect()
            #print("framegen() collect")

    def send_frame(idx, pp):
        cs, h = pp
        while True:
            ee = ''
            try:
                img=next(webstream.pic)
                #print("%d:send frame..." % idx)
                cs.send(b'%s' % h)
                cs.send(img)
                cs.send(b'\r\n')  # send and flush the send buffer
                #print("send frame...ok")
            except Exception as e:
                ee = str(e)
                print(">>>>" + ee)
            if ee == '':
                time.sleep(0.005)  # try as fast as we can
            else:
                break

    def processReq(idx, cs, rq):
       rqp = rq[1].split('/')
       args1 = str(rqp[1])
       args2 = str(rqp[2])
       if rqp[1] == 'apikey': # Must have /apikey/<REQ>
          if args1 == 'webcam':
             cs.send(b'%s' % webstream.hdr['live'])
          elif args2.startswith('live'): # start streaming
             cs.send(b'%s' % webstream.hdr['stream'])
             webstream.send_frame(idx, [cs, webstream.hdr['frame']])
          elif args2.startswith('snap'):
             try:
                img=next(webstream.pic)
                cs.send(b'%s %d\r\n\r\n' % (webstream.hdr['snap'], len(img)))
                cs.send(img)
             except:
                pass
          else: #
             cs.send(b'%s' % webstream.hdr['none'])
       else:
          cs.send(b'%s' % webstream.hdr['OK'])

    def srv(idx):
        ee = ''
        sa = webstream.ss
        sa.settimeout(0.05) # in sec NB! default browser timeout (5-15 min)
        while True:
            try: 
                #print('wait accept...')
                cs, ca = sa.accept()
                cs.settimeout(0.5) # in sec
            except Exception as e:
                ee = str(e)
                if(ee != '[Errno 11] EAGAIN'):
                    print(str(idx) + ":accept except:"+ee)
                continue
            
            try:
                r = cs.recv(1024)
                ms = r.decode('utf-8')
                rq = ms.split(' ')
                print(str(idx) + ":process:", rq[0], rq[1], ca)
                #print(str(idx) + ':recv ok')
            except Exception as e:
                #ee = str(e)
                print(str(idx) + ":recv except:"+ee)
                webstream.clean_up(cs)
                continue
                
            
            if ms.find('favicon.ico') >= 0:
                print(str(idx) + ":find('favicon.ico')")
                cs.send(b'%s' % webstream.hdr['favicon']) # handle favicon request early
                webstream.clean_up(cs)
                continue
            else:
                try:
                    webstream.processReq(idx, cs, rq)
                    #print(str(idx) + ':process ok')
                    webstream.clean_up(cs)
                except Exception as e:
                    print(str(idx) + ":processReq err:" + str(e))
