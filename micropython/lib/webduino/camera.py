import time, machine, camera, ubinascii, gc

class Camera():
    
    def init():
        try:
            Camera.initState
        except:
            Camera.initState = 0
        if Camera.initState is not 1:
            try:
                camera.deinit()
                #camera.init(0, format=camera.JPEG,xclk_freq=camera.XCLK_20MHz)
                #camera.init(0, format=camera.JPEG,xclk_freq=camera.XCLK_20MHz)
                camera.init(0, format=camera.JPEG)
                if(Camera.resolution == 'res1'):
                    camera.framesize(camera.FRAME_QVGA)     # 320 x 240
                elif(Camera.resolution == 'res2'):
                    camera.framesize(camera.FRAME_VGA)      # 640 x 480
                elif(Camera.resolution == 'res3'):
                    camera.framesize(camera.FRAME_SVGA)     # 800 x 600           
                #camera.framesize(camera.FRAME_XGA)  #O
                #camera.quality(10)
                camera.flip(1)
                #time.sleep(0.1)
                #Camera.initState = 1
            except:
                print("Camera exception !!!")
                Camera.initState = -1
                machine.reset()
                pass
            

 
    def snapshot():
        jpg = camera.capture()
        image = ubinascii.b2a_base64(jpg)
        del jpg
        time.sleep(0.1)
        gc.collect()
        return image

    def capture():
        gc.collect()
        return camera.capture()