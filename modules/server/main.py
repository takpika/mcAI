import json, os, psutil, socket, requests, argparse, subprocess, threading
from logging import getLogger, DEBUG, StreamHandler, Formatter

logger = getLogger(__name__)
logger.setLevel(DEBUG)
logger_handler = StreamHandler()
logger_formatter = Formatter(fmt='%(asctime)-15s [%(name)s] %(message)s')
logger_handler.setFormatter(logger_formatter)
logger.addHandler(logger_handler)

SERV_TYPE = "minecraft"

if os.path.exists("server.properties"):
    with open("server.properties", "r") as f:
        data = f.read()
    data = data.replace("online-mode=true", "online-mode=false")
    data = data.replace("difficulty=easy", "difficulty=hard")
    with open("server.properties", "w") as f:
        f.write(data)

parser = argparse.ArgumentParser(
    prog='server.py',
    description='mcAI Learning Agent',
    add_help = True
)
parser.add_argument('-i', '--interface', help='Interface', default="eth0", type=str)
args = parser.parse_args()

if_addrs = psutil.net_if_addrs()
if not args.interface in if_addrs:
    logger.error("Interface not found:", args.interface)
    exit(1)
ip = None
for addr in if_addrs[args.interface]:
    if addr.family == socket.AF_INET:
        ip = addr.address

if ip == None:
    logger.error("IPv4 address required.")
    exit(2)
logger.info("Your IP: "+ip)
lan_addr = ""
for i in range(3):
    lan_addr += ip.split(".")[i] + "."

def ping(ip):
    devnull = open("/dev/null", "wb")
    result = subprocess.run(["ping", ip, "-c", "1", "-w", "1"], stdout=devnull, stderr=devnull)
    devnull.close()
    return result.returncode == 0

CENTRAL_IP = None
logger.info("Searching for Central Server...")
def search_central(start, end):
    global CENTRAL_IP
    for x in range(start, end):
        try:
            if lan_addr + str(x) != ip and CENTRAL_IP == None:
                if ping(lan_addr+str(x)):
                    res = requests.get("http://%s:%d/hello" % (lan_addr+str(x), 8000))
                    if res.status_code != 200:
                        continue
                    data = json.loads(res.text)
                    if not "info" in data:
                        continue
                    if data["info"]["type"] == "central":
                        CENTRAL_IP = lan_addr + str(x)
                        break
        except:
            pass
ts = [threading.Thread(target=search_central, args=(i*64, (i+1)*64)) for i in range(4)]
for t in ts:
    t.start()
for t in ts:
    t.join()

if CENTRAL_IP == None:
    logger.error("Central Server not found")
    exit(3)
logger.info("Central Server IP: " + CENTRAL_IP)

send_data = {
    "type": "register",
    "info": {
        "type": SERV_TYPE.lower(),
        "ip": ip
    }
}
trys = 0

while requests.get("http://%s:%d/check?type=%s&ip=%s" % (CENTRAL_IP, 8000, SERV_TYPE, ip)).status_code != 200:
    requests.post("http://%s:%d/" % (CENTRAL_IP, 8000), json=send_data)
    trys += 1
    if trys > 10:
        logger.error("Register Failed")
        exit(4)

subprocess.run(["/usr/bin/screen", "-Dm", "-S", "minecraft", "/home/%s/run.sh" % (os.getlogin())])