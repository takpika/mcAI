from math import sqrt
import subprocess, requests, json, pynput, screeninfo, urllib.parse, os, argparse, threading, mcai, psutil, socket, cv2, random, pyautogui, hashlib, traceback, math
from mss import mss
from PIL import ImageDraw, Image
from time import sleep, time
import numpy as np
from logging import getLogger, DEBUG, StreamHandler, Formatter
import gc
from pmc import PortableMinecraft

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

logger = getLogger(__name__)
logger.setLevel(DEBUG)
logger_handler = StreamHandler()
logger_formatter = Formatter(fmt='%(asctime)-15s [%(name)s] %(message)s')
logger_handler.setFormatter(logger_formatter)
logger.addHandler(logger_handler)

SERV_TYPE = "client"
HOSTNAME = hashlib.md5(os.uname()[1].encode()).hexdigest()[:16]

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

CHECKING_REGISTER = False
CHECK_COUNT = 0
LAST_CHECK = 0

def check_registered():
    global CHECKING_REGISTER
    global CHECK_COUNT
    if not CHECKING_REGISTER and CHECK_COUNT % 10 == 0:
        result = requests.get("http://%s:%d/check?type=%s" % (CENTRAL_IP, 8000, SERV_TYPE)).status_code == 200
    else:
        result = True
    CHECK_COUNT += 1
    if CHECK_COUNT >= 10:
        CHECK_COUNT = 0
    return result

def register():
    global LAST_CHECK
    if LAST_CHECK == int(time()):
        return
    LAST_CHECK = int(time())
    send_data = {
        "type": "register",
        "info": {
            "type": SERV_TYPE.lower(),
            "hostname": HOSTNAME
        }
    }
    trys = 0
    while not check_registered():
        requests.post("http://%s:%d/" % (CENTRAL_IP, 8000), json=send_data)
        trys += 1
        if trys > 10:
            logger.error("Register Failed")
            exit(4)

register()
logger.info("Waiting for Central Server to configuration...")
while True:
    res = requests.get("http://%s:%d/config?type=%s" % (CENTRAL_IP, 8000, SERV_TYPE))
    if res.status_code == 200:
        config = json.loads(res.text)["config"]
        break
    sleep(10)

for key in config.keys():
    if type(config[key]) == str:
        config[key] = config[key].replace("__HOME__", os.getenv('HOME'))
        config[key] = config[key].replace("__WORKDIR__", os.getcwd())

PORT = config["port"]
SERVER = config["mc_server"]
L_SERVER = config["learn_server"]
MC_FOLDER = config["mc_folder"]
WORK_DIR = config["work_dir"]

WIDTH = config["resolution"]["x"]
HEIGHT = config["resolution"]["y"]

sct = mss()

VERSION = 0
AI_COUNT = 0
AI_USING = False
DOWNLOAD_LOCK = False
AI_UPDATE_LOCK = False
FORCE_QUIT = False

vfp = os.path.join(WORK_DIR, "version.json")
if os.path.exists(vfp):
    with open(vfp, "r") as f:
        version = json.loads(f.read())
        VERSION = version["version"]
        AI_COUNT = version["count"]

KEYS = ["q", "w", "e", "a", "s", "d", "shift", "space", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
pyautogui.PAUSE = 0.0

effects = ["slowness", "blindness", "weakness", "poison", "wither"]

screen = screeninfo.get_monitors()[0]
mouse = pynput.mouse.Controller()
mbt = pynput.mouse.Button
pos = mouse.position

with open(config["char_file"], "r") as f:
    chars = json.loads(f.read())

CHARS_COUNT = len(chars["chars"])
CHARS_LIMIT = config["chat_chars_limit"]

FRAME_LIMIT = config["frame_record_limit"]

def clear_keyboard():
    for k in KEYS:
        handle_keyboard(k, False)

def clear_mouse():
    mouse.release(mbt.left)
    mouse.release(mbt.right)
    subprocess.run(["xinput", "enable", "10"])

def clear_all():
    clear_keyboard()
    clear_mouse()

def handle_keyboard(k : str, value : bool):
    if value:
        pyautogui.keyDown(k)
    else:
        pyautogui.keyUp(k)

def handle_mouse(k : str, value : bool):
    if k == "left":
        if value:
            mouse.press(mbt.left)
        else:
            mouse.release(mbt.left)
    else:
        if value:
            mouse.press(mbt.right)
        else:
            mouse.release(mbt.right)


def conv_char(char : str):
    data = np.zeros((CHARS_COUNT))
    for i in range(CHARS_COUNT):
        if chars["chars"][i] == char:
            data[i] = 1
    return data

def bin_to_char(bin : np.ndarray):
    return chars["chars"][np.argmax(bin)]

def bin_to_name(bin : np.ndarray):
    name = ""
    for b in bin:
        char = bin_to_char(b)
        if char != "\n":
            name += char
        else:
            break
    return name

def conv_name(name : str):
    remain = 6 - len(name)
    data = [conv_char(name[i]) for i in range(len(name))]
    for i in range(remain):
        data.append(conv_char("\n"))
    return data

def move_center():
    pos = mouse.position
    mouse.move(int(screen.width/2-pos[0]), int(screen.height/2-pos[1]))

def check_mousecursor():
    pos = mouse.position
    if (pos[0] < screen.width/2-WIDTH/2) or pos[0] > screen.width/2+WIDTH/2:
        move_center()
    if (pos[1] < screen.height/2-HEIGHT/2) or pos[1] > screen.height/2+HEIGHT/2:
        move_center()

def drawPointer(img : Image.Image):
    draw = ImageDraw.Draw(img)
    pos = mouse.position
    draw.point(((pos[0]-int(screen.width/2-WIDTH/2), pos[1]-int(screen.height/2-HEIGHT/2))), fill=(255,0,0))
    return img

def getBit(value : int, bit : int):
    return value >> bit & 0b1

def convBit(value : float):
    value[value>=0.5] = 1
    value[value<0.5] = 0
    data = 0
    for i in range(7,-1,-1):
        try:
            if value[i] != np.nan:
                data = int(value[i]) << i | data
            else:
                data = 0 << i | data
        except:
            data = 0 << i | data
    return data

def send_learnData(hashID : str, endFramePos : int):
    global learn_data, config, videoFrames, L_SERVER, SERVER
    if hashID in learn_data:
        if len(learn_data[hashID]) >= 2:
            try:
                headers = {
                    'content-type': 'application/octet-stream',
                    'id': hashID,
                    'width': str(WIDTH),
                    'height': str(HEIGHT),
                    'frameCount': str(endFramePos)
                }
                requests.post("http://%s:%d/videoND" % (L_SERVER, PORT), data=videoFrames[:endFramePos].tobytes(), headers=headers)
                headers['content-type'] = 'application/json'
                sendData = {
                    "health": hp,
                    "data": learn_data[hashID]
                }
                requests.post("http://%s:%d/" % (L_SERVER, PORT), json=sendData, headers=headers)
            except requests.exceptions.ConnectionError:
                res = requests.get("http://%s:%d/config?type=%s" % (CENTRAL_IP, 8000, SERV_TYPE))
                if res.status_code == 200:
                    config = json.loads(res.text)["config"]
                    L_SERVER = config["learn_server"]
                    SERVER = config["mc_server"]
    learn_data.clear()

def startRecording():
    global videoFramePos
    global learn_data
    threading.Thread(target=download_update).start()
    hashID = json.loads(requests.get('http://%s:%d/id' % (CENTRAL_IP, PORT)).text)["info"]["id"]
    videoFramePos = 0
    learn_data[hashID] = []
    return hashID

def stopRecording(hashID : str, endFramePos : int):
    threading.Thread(target=send_learnData, args=(hashID, endFramePos)).start()

def check_version():
    data = json.loads(requests.get("http://%s:%d/" % (L_SERVER, PORT)).text)
    current = data["version"]
    count = data["count"]
    return current, count

def download_update():
    global DOWNLOAD_LOCK
    global AI_UPDATE_LOCK
    global VERSION, AI_COUNT
    modelFiles = ["model.h5"]
    if not DOWNLOAD_LOCK:
        DOWNLOAD_LOCK = True
        try:
            currentVersion, currentCount = check_version()
            if currentVersion <= 0:
                DOWNLOAD_LOCK = False
                for modelfile in modelFiles:
                    if os.path.exists(os.path.join(WORK_DIR, modelfile)):
                        os.remove(os.path.join(WORK_DIR, modelfile))
                if os.path.exists(os.path.join(WORK_DIR, "version.json")):
                    os.remove(os.path.join(WORK_DIR, "version.json"))
                return
            if os.path.exists("version.json"):
                with open("version.json", "r") as f:
                    versionData = json.loads(f.read())
                    VERSION = versionData["version"]
                    AI_COUNT = versionData["count"]
            if currentVersion > VERSION:
                logger.info("AI Model New Version Available!")
                for modelfile in modelFiles:
                    res = requests.get("http://%s:%d/%s" % (L_SERVER, PORT, modelfile))
                    with open(os.path.join(WORK_DIR, modelfile), "wb") as f:
                        f.write(res.content)
                while AI_USING:
                    sleep(0.1)
                AI_UPDATE_LOCK = True
                actor.load_weights(os.path.join(WORK_DIR, "model.h5"))
                AI_UPDATE_LOCK = False
                VERSION = currentVersion
                AI_COUNT = currentCount
                with open("version.json", "w") as f:
                    f.write(json.dumps({
                        "version": VERSION,
                        "count": AI_COUNT
                    }))
                logger.info("AI Updated")
            DOWNLOAD_LOCK = False
        except:
            for modelfile in modelFiles:
                if os.path.exists(os.path.join(WORK_DIR, modelfile)):
                    os.remove(os.path.join(WORK_DIR, modelfile))
            if os.path.exists("version.json"):
                subprocess.run(["rm", "version.json"])
            AI_UPDATE_LOCK = False
            VERSION = 0
            AI_COUNT = 0
            DOWNLOAD_LOCK = False
            logger.error("AI Update Failed")

def get_available_chat_name(name):
    res = requests.get("http://%s:%d/chat?hostname=%s" % (CENTRAL_IP, 8000, HOSTNAME))
    if res.status_code != 200:
        return ""
    else:
        data = json.loads(res.text)
        return data["info"]["name"]

def send_chat(name, message):
    logger.info("Send Chat: %s %s" % (name, message))
    requests.get("http://localhost:%d/?name=%s&message=%s" % (PORT, name, message))

def send_chat_function(name, message):
    op_name = get_available_chat_name(name)
    if op_name != "":
        send_chat(op_name, urllib.parse.quote(message))

def get_newName():
    while True:
        res = json.loads(requests.get("http://%s:%d/name?hostname=%s" % (CENTRAL_IP, PORT, HOSTNAME)).text)
        if res['status'] == 'ok':
            break
        register()
    return res["info"]["name"]

def end_session(hashID):
    global model, videoFramePos
    mcai.clearSession()
    gc.collect(2)
    clear_all()
    if hashID in learn_data:
        stopRecording(hashID, videoFramePos)

def hostname2name(hostname):
    data = json.loads(requests.get('http://%s:%d/hostname?hostname=%s' % (CENTRAL_IP, PORT, hostname)).text)
    if data['status'] == 'ok':
        if data['info']['name'] != '':
            return data['info']['name']
    return "Dummy"

def force_quit():
    global FORCE_QUIT
    FORCE_QUIT = True
    logger.debug("Force Quit")
    try:
        while True:
            res = requests.get("http://localhost:%d/?close=true" % (PORT))
            if res.status_code > 0:
                subprocess.run(["killall", "-9", "java"])
            else:
                break
            sleep(1)
    except:
        exit(10)

def pos_distance(pos1, pos2):
    return sqrt((pos1[0]-pos2[0])**2+(pos1[1]-pos2[1])**2+(pos1[2]-pos2[2])**2)

videoFrames, videoFramePos = np.empty((FRAME_LIMIT, HEIGHT, WIDTH, 3), dtype="uint8"), 0

model = mcai.Actor(WIDTH=WIDTH, HEIGHT=HEIGHT, CHARS_COUNT=CHARS_COUNT)
actor = model.buildModel()
ptmc = PortableMinecraft(version=config["version"], name=HOSTNAME, resol="%dx%d" % (WIDTH, HEIGHT), server=SERVER)

learn_data = {}

if __name__ == "__main__":
    try:
        while True:
            mc_thread = threading.Thread(target=ptmc.start)
            mc_thread.start()
            sleep(0.1)
            while True:
                if not ptmc.running: break
                try:
                    requests.get("http://localhost:%d/" % (PORT))
                    break
                except:
                    sleep(0.1)
                    continue
            if not ptmc.running: continue
            mc_start_time = time()
            mon = {'top': int(screen.height/2-HEIGHT/2), 'left': int(screen.width/2-WIDTH/2), 'width': WIDTH, 'height': HEIGHT}
            FORCE_QUIT = False
            played = False
            while True:
                get_newName()
                if FORCE_QUIT: break
                send_message_data = ""
                hashID = startRecording()
                mem = np.random.random((2**8, 8))
                if os.path.exists(os.path.join(WORK_DIR, "model.h5")):
                    actor.load_weights(os.path.join(WORK_DIR, "model.h5"))
                x, y = 0, 0
                mes_id = 0
                last = time()
                messages = []
                mem_reg, mem_reg2 = 0x0, 0x0
                char_at = 0
                hp = 0.0
                playStartTime = -1
                playFrameCounts = 0
                nextHunger = time()
                jumpCount = 0
                beforeHp, criticalHp = 8, 999999
                randomSeed = 0.5 * random.random()
                edit_char = ""
                inscreen = False
                before_key = [False for _ in KEYS]
                head_topbtm_time, headProcessed = -1, False
                last_pos, last_dir, last_change, last_change_pos = (-1, -1, -1), (-1, -1), -1, -1
                position_history = []
                afkStartTime, afkProcessed = -1, False
                newbie, newbieDamage, newbieDamageChecked = True, False, False
                while True:
                    if not ptmc.running:
                        FORCE_QUIT = True
                        break
                    if not hashID in learn_data:
                        learn_data[hashID] = []
                    url = "http://localhost:%d/" % (PORT)
                    send_data = {}
                    if (x != 0 and not inscreen):
                        send_data["x"] = float(x)
                    if (y != 0 and not inscreen):
                        send_data["y"] = float(y)
                    if (mes_id > 0):
                        send_data["checked"] = mes_id
                    mes_id = 0
                    failure = 0
                    while True:
                        try:
                            if (len(list(send_data.keys())) > 0):
                                data = json.loads(requests.get("%s?%s" % (url, urllib.parse.urlencode(send_data))).text)
                            else:
                                data = json.loads(requests.get(url).text)
                            break
                        except:
                            failure += 1
                        if failure >= 10:
                            logger.error("Connection Error")
                            end_session(hashID)
                            subprocess.run(["killall", "-9", "java"])
                            exit(10)
                    if data["screen"]:
                        if "net.minecraft.client.gui.screens.DisconnectedScreen" in data["screenInfo"]["id"]:
                            logger.warning("Disconnected. Auto restart...")
                            end_session(hashID)
                            force_quit()
                            break
                    if data["playing"]:
                        played = True
                        FPS = -1
                        img = sct.grab(mon)
                        image = Image.frombytes('RGB', (img.width, img.height), img.rgb)
                        if data["player"]["gamemode"] != "SURVIVAL":
                            for _ in range(10):
                                try:
                                    data = json.loads(requests.get("http://%s:%d/gamemode?name=%s&mode=survival" % (SERVER, PORT, HOSTNAME)).text)
                                    if data["status"] == "ok":
                                        break
                                    sleep(0.1)
                                except:
                                    pass
                            sleep(1)
                            continue
                        if newbie:
                            for _ in range(10):
                                datae = json.loads(requests.get("http://%s:%d/effect?name=%s&clear=true" % (SERVER, PORT, HOSTNAME)).text)
                                if datae["status"] != "ok":
                                    logger.debug("Failed to clear effects")
                                    continue
                                datae = json.loads(requests.get("http://%s:%d/effect?name=%s&effect=%s&level=%d&duration=%d" % (SERVER, PORT, HOSTNAME, "hunger", 255, 2)).text) # before: 255 3 sec
                                if datae["status"] != "ok":
                                    logger.debug("Failed to add effect: hunger")
                                    continue
                                nextHunger += 120
                                datae = json.loads(requests.get("http://%s:%d/effect?name=%s&effect=%s&level=%d&duration=%d" % (SERVER, PORT, HOSTNAME, "strength", 0, 999999)).text)
                                if datae["status"] != "ok":
                                    logger.debug("Failed to add effect: strength")
                                    continue
                                for effect in effects:
                                    if random.random() < 0.01:
                                        level = int((random.random() ** 2) * 10)
                                        datae = json.loads(requests.get("http://%s:%d/effect?name=%s&effect=%s&level=%d&duration=999999" % (SERVER, PORT, HOSTNAME, effect, level)).text)
                                        if datae["status"] != "ok":
                                            logger.debug("Failed to add effect: %s" % (effect))
                                            continue
                                break
                            newbie = False
                        if newbieDamage and not newbieDamageChecked:
                            if data["player"]["health"] <= 8:
                                newbieDamageChecked = True
                            else:
                                newbieDamage = False
                        if data["player"]["health"] > 8 and not newbieDamage:
                            datae = json.loads(requests.get("http://%s:%d/effect?name=%s&effect=%s&level=%d&duration=%d" % (SERVER, PORT, HOSTNAME, "instant_damage", 1, 1)).text)
                            if datae["status"] != "ok":
                                logger.debug("Failed to add effect: instant_damage")
                                continue
                            newbieDamage = True
                            sleep(1)
                            continue
                        if playStartTime == -1:
                            playStartTime = time()
                        playFrameCounts += 1
                        FPS = playFrameCounts / (time() - playStartTime)
                        if time() > nextHunger or jumpCount >= FPS * 10:
                            if jumpCount >= FPS * 10:
                                jumpCount = 0
                            datae = json.loads(requests.get("http://%s:%d/effect?name=%s&effect=%s&level=%d&duration=%d" % (SERVER, PORT, HOSTNAME, "hunger", 39, 1)).text)
                            if datae["status"] == "ok":
                                nextHunger += 120
                        if data["player"]["health"] <= beforeHp - 10:
                            criticalHp = data["player"]["health"] + 5
                            datae = json.loads(requests.get("http://%s:%d/effect?name=%s&effect=%s&level=%d&duration=%d" % (SERVER, PORT, HOSTNAME, "slowness", 5, 3600)).text)
                            datae = json.loads(requests.get("http://%s:%d/effect?name=%s&effect=%s&level=%d&duration=%d" % (SERVER, PORT, HOSTNAME, "mining_fatigue", 1, 3600)).text)
                            datae = json.loads(requests.get("http://%s:%d/effect?name=%s&effect=%s&level=%d&duration=%d" % (SERVER, PORT, HOSTNAME, "weakness", 0, 3600)).text)
                            datae = json.loads(requests.get("http://%s:%d/effect?name=%s&effect=%s&level=%d&duration=%d" % (SERVER, PORT, HOSTNAME, "jump_boost", 254, 3600)).text)
                        if data["player"]["health"] >= criticalHp:
                            datae = json.loads(requests.get("http://%s:%d/effect?name=%s&clear=true" % (SERVER, PORT, HOSTNAME)).text)
                            criticalHp = 999999
                        beforeHp = data["player"]["health"]
                        if data["player"]["death"]:
                            logger.info("Dead")
                            if hashID in learn_data:
                                if len(learn_data[hashID]) > 0:
                                    learn_data[hashID][-1]["health"] = 0
                            end_session(hashID)
                            for _ in range(100):
                                data = json.loads(requests.get(url).text)
                                if data["playing"]:
                                    if data["player"]["death"]:
                                        pyautogui.keyDown("tab")
                                        sleep(0.2)
                                        pyautogui.keyUp("tab")
                                        sleep(0.2)
                                        pyautogui.keyDown("enter")
                                        sleep(0.2)
                                        pyautogui.keyUp("enter")
                                        continue
                                sleep(0.1)
                                break
                            if data["playing"]:
                                if data["player"]["death"]:
                                    logger.error("Failed to respawn")
                                    force_quit()
                            break
                        if data["screen"]:
                            if data["screenInfo"]["pause"]:
                                logger.info("Pause")
                                pyautogui.keyDown("esc")
                                sleep(0.2)
                                pyautogui.keyUp("esc")
                                continue
                            inscreen = True
                            mouse.move(int(x), int(y))
                            check_mousecursor()
                            image = drawPointer(image)
                            if data["screenInfo"]["edit"]:
                                send_message_data = ""
                                char_k = None
                                if edit_char == "\n":
                                    char_k = "enter"
                                elif edit_char == "\t":
                                    char_k = "esc"
                                elif edit_char == "NONE":
                                    char_k = None
                                elif edit_char == "DEL":
                                    char_k = "backspace"
                                else:
                                    char_k = edit_char
                                if char_k != None:
                                    pyautogui.keyDown(char_k)
                                    sleep(0.1)
                                    pyautogui.keyUp(char_k)
                        else:
                            inscreen = False
                        dir_X = data["player"]["direction"]["x"]
                        if dir_X < 0:
                            dir_X *= -1
                        if dir_X > 80:
                            if head_topbtm_time == -1:
                                head_topbtm_time = time()
                            else:
                                if time() - head_topbtm_time >= 3 and len(learn_data[hashID]) >= 2 and not headProcessed:
                                    logger.info("Head spinning")
                                    datae = json.loads(requests.get("http://%s:%d/effect?name=%s&effect=%s&level=%d&duration=%d" % (SERVER, PORT, HOSTNAME, "hunger", 255, 60)).text)
                                    headProcessed = True
                        else:
                            head_topbtm_time = -1
                            headProcessed = False
                        pos = (int(data["player"]["pos"]["x"]), int(data["player"]["pos"]["y"]), int(data["player"]["pos"]["z"]))
                        pos_float = (data["player"]["pos"]["x"], data["player"]["pos"]["y"], data["player"]["pos"]["z"])
                        dir = (int(data["player"]["direction"]["x"]), int(data["player"]["direction"]["y"]))
                        position_history.append(pos_float)
                        if len(position_history) > FPS * 60 * 60:
                            position_history.pop(0)
                        average_pos = (0, 0, 0)
                        for p in position_history:
                            average_pos = (average_pos[0] + p[0], average_pos[1] + p[1], average_pos[2] + p[2])
                        average_pos = (average_pos[0] / len(position_history), average_pos[1] / len(position_history), average_pos[2] / len(position_history))
                        if pos_distance(average_pos, pos_float) <= min(len(position_history)/FPS*0.01, 10):
                            if afkStartTime == -1:
                                afkStartTime = time()
                            else:
                                if time() - afkStartTime >= 5 and not afkProcessed:
                                    logger.info("AFK")
                                    datae = json.loads(requests.get("http://%s:%d/effect?name=%s&effect=%s&level=%d&duration=%d" % (SERVER, PORT, HOSTNAME, "hunger", 255, 60)).text)
                                    afkProcessed = True
                        else:
                            afkStartTime = -1
                            afkProcessed = False
                        x_img = np.array(image).reshape((1, HEIGHT, WIDTH, 3)) / 255
                        x_reg = np.array([getBit(mem_reg, i) for i in range(7,-1,-1)])
                        x_mem = mem[mem_reg]
                        x_reg2 = np.array([getBit(mem_reg2, i) for i in range(7,-1,-1)])
                        x_mem2 = mem[mem_reg2]
                        if len(messages) > 0:
                            if not "name" in messages[0]:
                                messages[0]["name"] = hostname2name(messages[0]["author"])
                            elif messages[0]["name"] == "":
                                messages[0]["name"] = hostname2name(messages[0]["author"])
                            x_name = conv_name(messages[0]["name"])
                            x_mes = conv_char(messages[0]["message"][char_at])
                            char_at += 1
                            if char_at >= len(messages[0]["message"]):
                                char_at = 0
                                messages.pop(0)
                        else:
                            x_name = conv_name("")
                            x_mes = conv_char("\t")
                        while AI_UPDATE_LOCK:
                            sleep(1)
                            logger.info("Updating AI...")
                        AI_USING = True
                        ai_k, ai_m, ai_mem, ai_chat = actor.predict(model.make_input(
                            x_img, x_reg, x_mem, x_reg2, x_mem2, x_name, x_mes, 1
                        ), verbose=0)
                        if random.random() < randomSeed:
                            ai_k = np.random.random(ai_k.shape)
                            ai_m[0] = np.random.random(ai_m[0].shape) * 2 - 1
                            ai_m[1] = np.random.random(ai_m[1].shape)
                            for i in ai_mem:
                                i = np.random.random(i.shape)
                            ai_chat = np.random.random(ai_chat.shape)
                        AI_USING = False
                        ai_k = np.where(ai_k < 0.5, 0, 1)
                        ai_m[0] = np.clip(ai_m[0], -1, 1)
                        ai_m[1] = np.where(ai_m[1] < 0.5, 0, 1)
                        for i in range(len(ai_mem)):
                            if i == 1:
                                ai_mem[i] = np.clip(ai_mem[i], 0, 1)
                            ai_mem[i] = np.where(ai_mem[i] < 0.5, 0, 1)
                        ai_chat = np.where(ai_chat == np.max(ai_chat), 1, 0)
                        for i in range(len(KEYS)):
                            res = ai_k[0][i] >= 0.5
                            if res and KEYS[i] == "space":
                                jumpCount += 1
                            if before_key[i] != res:
                                handle_keyboard(KEYS[i], ai_k[0][i] >= 0.5)
                            before_key[i] = res
                        x = ai_m[0][0][0] * 20
                        y = ai_m[0][0][1] * 20
                        handle_mouse("left", ai_m[1][0][0] >= 0.5)
                        handle_mouse("right", ai_m[1][0][1] >= 0.5)
                        save_reg = convBit(ai_mem[0][0])
                        mem[save_reg] = ai_mem[1][0]
                        mem_reg = convBit(ai_mem[2][0])
                        mem_reg2 = convBit(ai_mem[3][0])
                        mes_char = bin_to_char(ai_chat[0])
                        if mes_char != "\n" and mes_char != "NONE" and not data["screen"]:
                            if mes_char == "DEL":
                                if len(send_message_data) > 1:
                                    send_message_data = send_message_data[:-1]
                                else:
                                    send_message_data = ""
                            elif mes_char == "\t":
                                threading.Thread(target=send_chat_function, args=(data["player"]["name"], send_message_data)).start()
                                send_message_data = ""
                            else:
                                send_message_data += mes_char
                        elif data["screen"]:
                            if data["screenInfo"]["edit"]:
                                edit_char = mes_char
                        if len(send_message_data) > CHARS_LIMIT:
                            send_message_data = send_message_data[:CHARS_LIMIT]
                        if random.random() < 0.1:
                            videoFrames[videoFramePos] = (x_img.reshape((HEIGHT,WIDTH,3))*255).astype("uint8")
                            videoFramePos += 1
                            this_frame = {
                                "health": data["player"]["health"],
                                "input": {
                                    "mem": {
                                        "reg": convBit(x_reg),
                                        "data": x_mem.tolist(),
                                        "reg2": convBit(x_reg2),
                                        "data2": x_mem2.tolist()
                                    },
                                    "chat": {
                                        "name": bin_to_name(x_name),
                                        "message": bin_to_char(x_mes)
                                    }
                                }, 
                                "output": {
                                    "keyboard": ai_k[0].tolist(),
                                    "mouse": {
                                        "dir": ai_m[0][0].tolist(),
                                        "button": ai_m[1][0].tolist()
                                    } ,
                                    "mem": {
                                        "save": convBit(ai_mem[0][0]),
                                        "mem": ai_mem[1][0].tolist(),
                                        "reg": convBit(ai_mem[2][0]),
                                        "reg2": convBit(ai_mem[3][0])
                                    },
                                    "chat": bin_to_char(ai_chat[0])
                                }
                            }
                            learn_data[hashID].append(this_frame)
                        if not hashID in learn_data:
                            hashID = startRecording()
                        elif len(learn_data[hashID]) > FRAME_LIMIT:
                            stopRecording(hashID)
                            hashID = startRecording()
                    else:
                        if played:
                            logger.warning("Logged out. Auto restart...")
                            end_session(hashID)
                            force_quit()
                            break
                        elif time() - mc_start_time > 300:
                            logger.warning("Maybe disconnected. Auto restart...")
                            end_session(hashID)
                            force_quit()
                            break
                    if len(data["message"]) > 0:
                        messages.append(data["message"][0])
                        logger.info("A message from " + data["message"][0]["author"] + " : " + data["message"][0]["message"])
                        mes_id = int(data["message"][0]["id"])
                    threading.Thread(target=register).start()
    except Exception as e:
        t = list(traceback.TracebackException.from_exception(e).format())
        for i in t:
            logger.error(i)
    finally:
        if not (hashID == "" or hashID == None):
            end_session(hashID)
        force_quit()
