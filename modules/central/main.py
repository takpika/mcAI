import json, argparse, threading, socket, requests, os
from time import sleep
from CentralHandler import CentralHandler
from mcai.module import ModuleCore

class Central(ModuleCore):
    def __init__(self, mul_group:str="224.1.1.1", mul_port:int=9999):
        super().__init__()
        self.mul_group = mul_group
        self.mul_port = mul_port
        self.clients = {}
        self.mc_server = None
        self.learn_server = None
        self.getLogger()
        if __name__ == "__main__":
            self.parseArgs()
            self.openNames()

    def udpServer(self):
        multicast_group = self.mul_group
        multicast_port = self.mul_port
        server_address = ("", multicast_port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(server_address)
        mreq = socket.inet_aton(multicast_group) + socket.inet_aton("0.0.0.0")
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        while True:
            data, address = sock.recvfrom(1024)
            self.logger.debug("Received multicast from %s" % (address[0]))
            data = json.loads(data.decode("utf-8"))
            sleep(0.5)
            if "type" in data:
                if data["type"] == "hello":
                    reply = {
                        "status": "ok",
                        "info": {
                            "type": "central"
                        }
                    }
                    for i in range(10):
                        sock.sendto(json.dumps(reply).encode("utf-8"), (address[0], 9999))
                        sleep(0.1)

    def start(self):
        udpThread = threading.Thread(target=self.udpServer)
        udpThread.daemon = True
        udpThread.start()
        server = self.ThreadedHTTPServer(("0.0.0.0", 8000), CentralHandler, self)
        server.serve_forever()

    def parseArgs(self):
        parser = argparse.ArgumentParser(
            prog='main.py',
            description='mcAI Central Agent',
            add_help = True
        )
        parser.add_argument('configFile', help='Config File (JSON)', type=argparse.FileType('r'))
        args = parser.parse_args()
        self.config = json.loads(args.configFile.read())
        args.configFile.close()

    def get_players(self):
        clientsCopy = self.clients.copy()
        players = {}
        for client in clientsCopy:
            try:
                data = json.loads(requests.get("http://%s:8000/" % (clientsCopy[client]["ip"])).text)
                if "playing":
                    players[data["player"]["name"]] = {
                        "name": clientsCopy[client]["name"],
                        "pos": data["player"]["pos"],
                        "dir": data["player"]["direction"]
                    }
                    continue
            except:
                pass
            self.clients.pop(client)
        return players

    def openConfig(self, configPath):
        with open(configPath, "r") as f:
            self.config = json.loads(f.read())

    def openNames(self):
        with open(self.config["files"]["name_file"].replace("__WORKDIR__", os.getcwd()), "r") as f:
            self.names = f.read().splitlines()

if __name__ == '__main__':
    central = Central()
    central.start()