from logging import getLogger, DEBUG, StreamHandler, Formatter
from http.server import HTTPServer
from socketserver import ThreadingMixIn
import os, json, requests, socket
from time import sleep, time

class ModuleCore:
    def __init__(self):
        self.SERV_TYPE = self.__class__.__name__.lower()
        self.LAST_REGISTER = -1

    def getLogger(self):
        self.logger = getLogger("%s (%s)" % (self.__class__.__name__, __name__))
        self.logger.setLevel(DEBUG)
        self.logger_handler = StreamHandler()
        self.logger_formatter = Formatter(fmt='%(asctime)-15s [%(name)s]: %(message)s')
        self.logger_handler.setFormatter(self.logger_formatter)
        self.logger.addHandler(self.logger_handler)

    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        def __init__(self, server_address: tuple, RequestHandlerClass, parent):
            self.parent = parent
            super().__init__(server_address=server_address, RequestHandlerClass=RequestHandlerClass)

    def searchCentral(self):
        if os.path.exists("central_host"):
            with open("central_host", "r") as f:
                self.CENTRAL_IP = f.read().replace("\n","")
            try:
                data = json.loads(requests.get("http://%s:%d/hello" % (self.CENTRAL_IP, 8000)).text)
                if data["status"] == "ok":
                    if data["info"]["type"] == "central":
                        return
                    if data["info"]["type"] == "unified" and "support" in data["info"]:
                        if "central" in data["info"]["support"]:
                            return
            except:
                pass
        self.CENTRAL_IP = None
        sendData = {
            "type": "hello"
        }
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 9999))
        sock.settimeout(1)
        for _ in range(10):
            sock.sendto(json.dumps(sendData).encode("utf-8"), ("224.1.1.1", 9999))
            try:
                data, addr = sock.recvfrom(1024)
                data = json.loads(data.decode("utf-8"))
                if data["status"] == "ok" and data["info"]["type"] == "central":
                    self.CENTRAL_IP = addr[0]
                    break
            except:
                pass
            if self.CENTRAL_IP != None:
                break
        sock.close()

    def register(self, ignore_time=False):
        if self.LAST_REGISTER == int(time()) and not ignore_time:
            return
        self.LAST_REGISTER = int(time())
        trys = 0
        send_data = {
            "type": "register",
            "info": {
                "type": self.SERV_TYPE.lower()
            }
        }
        if self.SERV_TYPE.lower() == "client":
            send_data["info"]["hostname"] = self.HOSTNAME
        while requests.get("http://%s:%d/check?type=%s%s" % (self.CENTRAL_IP, 8000, self.SERV_TYPE, "&hostname=%s" % (self.HOSTNAME) if self.SERV_TYPE.lower() == "client" else "")).status_code != 200:
            requests.post("http://%s:%d/" % (self.CENTRAL_IP, 8000), json=send_data)
            trys += 1
            if trys > 10:
                self.logger.error("Register Failed")
                exit(4)

    def getConfig(self):
        if self.CENTRAL_IP == None:
            return
        self.register()
        self.logger.info("Waiting for Central Server to configuration...")
        while True:
            res = requests.get("http://%s:%d/config?type=%s" % (self.CENTRAL_IP, 8000, self.SERV_TYPE))
            if res.status_code == 200:
                self.config = json.loads(res.text)["config"]
                break
            sleep(10)
        
        for key in self.config.keys():
            if type(self.config[key]) == str:
                self.config[key] = self.config[key].replace("__HOME__", os.getenv('HOME'))
                self.config[key] = self.config[key].replace("__WORKDIR__", os.getcwd())

    def bin2Char(self, bin) -> str:
        import numpy as np
        return self.chars["chars"][np.argmax(bin)]
    
    def bin2Name(self, bin):
        name = ""
        for b in bin:
            char = self.bin2Char(b)
            if char != "\n":
                name += char
            break
        return name

    def convChar(self, char: str):
        import numpy as np
        data = np.zeros((self.CHARS_COUNT))
        for i in range(self.CHARS_COUNT):
            if self.chars["chars"][i] == char:
                data[i] = 1
        return data
    
    def convName(self, name: str):
        remain = 6 - len(name)
        data = [self.convChar(name[i]) for i in range(len(name))]
        for i in range(remain):
            data.append(self.convChar("\n"))
        return data