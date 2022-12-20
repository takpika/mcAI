import json, os, socket, requests, subprocess
from logging import getLogger, DEBUG, StreamHandler, Formatter

logger = getLogger(__name__)
logger.setLevel(DEBUG)
logger_handler = StreamHandler()
logger_formatter = Formatter(fmt='%(asctime)-15s [%(name)s] %(message)s')
logger_handler.setFormatter(logger_formatter)
logger.addHandler(logger_handler)

SERV_TYPE = "minecraft"

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

subprocess.run(["/usr/bin/screen", "-DmS", "minecraft", "bash", "run.sh"])