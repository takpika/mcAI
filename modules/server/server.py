import json, os, socket, requests, subprocess, sys
from logging import getLogger, DEBUG, StreamHandler, Formatter
from time import sleep
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading, urllib.parse
from mcrcon import MCRcon
import random, traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed

from mcai.module import ModuleCore
from ServerHandler import ServerHandler

class Server(ModuleCore):
    def __init__(self):
        super().__init__()
        self.RCON_ADDRESS = "localhost"
        self.RCON_PORT = 25575
        self.RCON_PASSWORD = "mcai"
        self.getLogger()
        if __name__ == "__main__":
            self.logger.info("Searching for Central Server...")
            self.searchCentral()
            if self.CENTRAL_IP == None:
                self.logger.error("Central Server not found")
                exit(1)
            self.logger.info("Central Server IP: " + self.CENTRAL_IP)
            self.getConfig()
            self.setConfig()

    def setConfig(self):
        self.PORT: int = self.config["port"]

    def setupMCServer(self):
        if os.path.exists("eula.txt"):
            os.remove("eula.txt")
        with open("eula.txt", "w") as f:
            f.write("eula=true")

        if os.path.exists("server.properties"):
            with open("server.properties", "r") as f:
                data = f.read()
            data = data.replace("online-mode=true", "online-mode=false")
            data = data.replace("difficulty=easy", "difficulty=hard")
            with open("server.properties", "w") as f:
                f.write(data)

        if not os.path.exists("world/"):
            os.mkdir("world/")

        jsons = ["ops", "whitelist", "usercache", "banned-ips", "banned-players"]
        if not os.path.exists("server/"):
            os.mkdir("server/")
        for j in jsons:
            if not os.path.exists("server/%s.json" % j):
                with open("server/%s.json" % j, "w") as f:
                    f.write("[]")

    class CustomMCRcon(MCRcon):
        def __init__(self, host, password, port=25575, tlsmode=0, timeout=5):
            self.host = host
            self.password = password
            self.port = port
            self.tlsmode = tlsmode
            self.timeout = timeout

        def _read(self, length):
            self.socket.settimeout(self.timeout)
            data = b""
            while len(data) < length:
                data += self.socket.recv(length - len(data))
            return data

    def runCommand(self, command):
        while True:
            try:
                with self.CustomMCRcon(self.RCON_ADDRESS, self.RCON_PASSWORD, self.RCON_PORT) as mcr:
                    mcr.command(command)
                break
            except Exception as e:
                t = list(traceback.TracebackException.from_exception(e).format())
                for i in t:
                    self.logger.error(i)
                continue

    def checkServerRunning(self):
        try:
            with self.CustomMCRcon(self.RCON_ADDRESS, self.RCON_PASSWORD, self.RCON_PORT) as mcr:
                mcr.command("list")
            return True
        except:
            return False

    def randomApple(self):
        while not self.checkServerRunning():
            sleep(1)
        while True:
            self.runCommand("execute at @a run summon minecraft:item ~ ~100 ~ {Item:{id:\"minecraft:bread\",Count:1b},PickupDelay:0s,Tags:[\"randomFood\"],NoGravity:true}")
            self.runCommand("execute at @r run spreadplayers ~ ~ 0 30 false @e[tag=randomFood]")
            sleep(60)

    def startHTTPServer(self):
        server = self.ThreadedHTTPServer(("0.0.0.0", self.PORT), ServerHandler, self)
        server.serve_forever()

    def minecraftServer(self):
        subprocess.run(["bash", "run.sh"])

    def start(self):
        tasks = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            tasks.append(executor.submit(self.startHTTPServer))
            tasks.append(executor.submit(self.randomApple))
            tasks.append(executor.submit(self.minecraftServer))
            for future in as_completed(tasks):
                try:
                    future.result()
                except Exception as e:
                    t = list(traceback.TracebackException.from_exception(e).format())
                    for i in t:
                        self.logger.error(i)
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
                    exit(1)

if __name__ == "__main__":
    server = Server()
    server.start()