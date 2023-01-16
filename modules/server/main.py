import json, os, socket, requests, subprocess
from logging import getLogger, DEBUG, StreamHandler, Formatter
from time import sleep
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading, urllib.parse

logger = getLogger(__name__)
logger.setLevel(DEBUG)
logger_handler = StreamHandler()
logger_formatter = Formatter(fmt='%(asctime)-15s [%(name)s] %(message)s')
logger_handler.setFormatter(logger_formatter)
logger.addHandler(logger_handler)

SERV_TYPE = "server"

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
    env = os.environ
    if "CENTRAL_SERVICE_HOST" in env:
        CENTRAL_IP = env["CENTRAL_SERVICE_HOST"]
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
        for _ in range(10):
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
                subprocess.run("/usr/bin/screen -S minecraft -X eval 'stuff \"kill %s\"'\015" % query["name"][0], shell=True)
                status_code = 200
                response["status"] = "ok"
                response["msg"] = "Success"
            else:
                status_code = 400
                response["msg"] = "Bad Request"
        elif path == "/gamemode":
            if "name" in query and "mode" in query:
                subprocess.run("/usr/bin/screen -S minecraft -X eval 'stuff \"gamemode %s %s\"'\015" % (query["mode"][0], query["name"][0]), shell=True)
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

if __name__ == "__main__":
    t = threading.Thread(target=start_httpServer)
    t.daemon = True
    t.start()
    subprocess.run(["/usr/bin/screen", "-DmS", "minecraft", "bash", "run.sh"])