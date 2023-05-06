import json, os, socket, requests, subprocess, sys
from logging import getLogger, DEBUG, StreamHandler, Formatter
from time import sleep
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading, urllib.parse
from mcrcon import MCRcon

logger = getLogger(__name__)
logger.setLevel(DEBUG)
logger_handler = StreamHandler()
logger_formatter = Formatter(fmt='%(asctime)-15s [%(name)s] %(message)s')
logger_handler.setFormatter(logger_formatter)
logger.addHandler(logger_handler)

SERV_TYPE = "server"

RCON_ADDRESS = "localhost"
RCON_PORT = 25575
RCON_PASSWORD = "mcai"

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

CENTRAL_IP = None
logger.info("Searching for Central Server...")

def search_central():
    global CENTRAL_IP
    if os.path.exists("central_host"):
        with open("central_host", "r") as f:
            CENTRAL_IP = f.read().replace("\n","")
        try:
            data = json.loads(requests.get("http://%s:%d/hello" % (CENTRAL_IP, 8000)).text)
            if data["status"] == "ok" and data["info"]["type"] == "central":
                return
            else:
                CENTRAL_IP = None
        except:
            CENTRAL_IP = None
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
                CENTRAL_IP = addr[0]
                break
        except:
            pass
        if CENTRAL_IP != None:
            break
    sock.close()
        

search_central()

if CENTRAL_IP == None:
    logger.error("Central Server not found")
    exit(3)
logger.info("Central Server IP: " + CENTRAL_IP)

send_data = {
    "type": "register",
    "info": {
        "type": SERV_TYPE.lower()
    }
}
trys = 0

mcr = MCRcon(RCON_ADDRESS, RCON_PASSWORD, RCON_PORT)

def runCommand(command):
    global mcr
    while True:
        try:
            mcr.command(command)
            break
        except:
            mcr.disconnect()
            mcr.connect()
            continue
    
def checkServerRunning():
    try:
        mcr.command("list")
        return True
    except:
        return False

while requests.get("http://%s:%d/check?type=%s" % (CENTRAL_IP, 8000, SERV_TYPE)).status_code != 200:
    requests.post("http://%s:%d/" % (CENTRAL_IP, 8000), json=send_data)
    trys += 1
    if trys > 10:
        logger.error("Register Failed")
        exit(4)
        
logger.info("Waiting for Central Server to configuration...")
while True:
    res = requests.get("http://%s:%d/config?type=%s" % (CENTRAL_IP, 8000, SERV_TYPE))
    if res.status_code == 200:
        config = json.loads(res.text)["config"]
        break
    sleep(10)

PORT = config["port"]

if os.path.exists("config/toughasnails/temperature.toml"):
    with open("config/toughasnails/temperature.toml", "r") as f:
        data = f.read()
    data = data.replace("climate_clemency_duration = 6000", "climate_clemency_duration = 0")
    with open("config/toughasnails/temperature.toml", "w") as f:
        f.write(data)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parse_data = urllib.parse.urlparse(self.path)
        path = parse_data.path
        query = urllib.parse.parse_qs(parse_data.query)
        status_code = 404
        response = {
            "status": "ng",
            "msg": "Not Found"
        }
        if path == "/kill":
            if "name" in query:
                runCommand("kill %s" % query["name"][0])
                status_code = 200
                response["status"] = "ok"
                response["msg"] = "Success"
            else:
                status_code = 400
                response["msg"] = "Bad Request"
        elif path == "/gamemode":
            if "name" in query and "mode" in query:
                runCommand("gamemode %s %s" % (query["mode"][0], query["name"][0]))
                status_code = 200
                response["status"] = "ok"
                response["msg"] = "Success"
            else:
                status_code = 400
                response["msg"] = "Bad Request"
        elif path == "/effect":
            if "name" in query and "effect" in query and not "clear" in query:
                playerName = query["name"][0]
                effectName = query["effect"][0]
                level = int(query["level"][0]) if "level" in query else 1
                duration = int(query["duration"][0]) if "duration" in query else 999999
                runCommand("effect give %s %s %d %d true" % (playerName, effectName, duration, level))
                status_code = 200
                response["status"] = "ok"
                response["msg"] = "Success"
            elif "name" in query and "clear" in query:
                playerName = query["name"][0]
                effect = query["effect"][0] if "effect" in query else ""
                runCommand("effect clear %s %s" % (playerName, effect))
                status_code = 200
                response["status"] = "ok"
                response["msg"] = "Success"
            else:
                status_code = 400
                response["msg"] = "Bad Request"
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

def start_httpServer():
    server = ThreadedHTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()

def randomApple():
    while not checkServerRunning():
        sleep(1)
    while True:
        runCommand("execute at @a run summon minecraft:item ~ ~100 ~ {Item:{id:\"minecraft:apple\",Count:1b},PickupDelay:0s,Tags:[\"randomApple\"],NoGravity:true}")
        runCommand("execute at @r run spreadplayers ~ ~ 10 30 false @e[tag=randomApple]")
        sleep(60)

if __name__ == "__main__":
    targets = [start_httpServer, randomApple]
    for target in targets:
        thread = threading.Thread(target=target)
        thread.start()
        thread.daemon = True
    subprocess.run(["bash", "run.sh"])
    sys.exit(1)