import usocket

class GDriver:

    def setScriptURL(scriptURL):
        GDriver.scriptURL = scriptURL

    def setFolderId(folderId):
        GDriver.folderId = folderId
        
    def upload(image,filename):
        url = 'https://script.google.com/macros/s/'+GDriver.scriptURL+'/exec'
        myFilename = "filename="+str(filename)+"&folderId="+GDriver.folderId+"&data="
        data = myFilename + image.decode()
        try:
            proto, dummy, host, path = url.split("/", 3)
        except ValueError:
            proto, dummy, host = url.split("/", 2)
            path = ""
        if proto == "http:":
            port = 80
        elif proto == "https:":
            import ussl
            port = 443
        else:
            raise ValueError("Unsupported protocol: " + proto)
        if ":" in host:
            host, port = host.split(":", 1)
            port = int(port)

        ai = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)
        ai = ai[0]
        s = usocket.socket(ai[0], ai[1], ai[2])
        s.connect(ai[-1])
        if proto == "https:":
            s = ussl.wrap_socket(s, server_hostname=host)
        s.write(b"%s /%s HTTP/1.0\r\n" % ("POST", path))
        s.write(b"Host: %s\r\n" % host)
        s.write(b"Content-Length: %d\r\n" % len(data))
        s.write(b"Content-Type: application/x-www-form-urlencoded\r\n")
        s.write(b"\r\n")
        s.write(data)
        # response
        l = s.readline()
        l = l.split(None, 2)
        status = int(l[1])
        response = ""
        if len(l) > 2:
            reason = l[2].rstrip()
        while True:
            l = s.readline().decode("utf-8")
            if len(l)>9 and l[0:9]=='Location:': response = l[10:-2]
            if not l or l == "\r\n\r\n": break
        return response      