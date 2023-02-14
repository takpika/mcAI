from math import sqrt
import subprocess, requests, json, pynput, screeninfo, urllib.parse, os, argparse, threading, mcai, psutil, socket, cv2, random, pyautogui, hashlib
from mss import mss
from PIL import ImageDraw, Image
from time import sleep, time
import numpy as np
from logging import getLogger, DEBUG, StreamHandler, Formatter
import gc
from pmc import PortableMinecraft

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

def register(ignore_time=False):
    global LAST_CHECK
    if LAST_CHECK == int(time()) and not ignore_time:
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
VIDEO_FILE = config["video_file"]

WIDTH = config["resolution"]["x"]
HEIGHT = config["resolution"]["y"]

sct = mss()

VERSION = 0
AI_USING = False
DOWNLOAD_LOCK = False
AI_UPDATE_LOCK = False
FORCE_QUIT = False

vfp = os.path.join(WORK_DIR, "version")
if os.path.exists(vfp):
    with open(vfp, "r") as f:
        VERSION = int(f.read())

KEYS = ["q", "w", "e", "a", "s", "d", "shift", "space", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
pyautogui.PAUSE = 0.0

effects = ["slowness", "blindness", "hunger", "weakness", "poison", "wither", "toughasnails:thirst"]

screen = screeninfo.get_monitors()[0]
mouse = pynput.mouse.Controller()
mbt = pynput.mouse.Button
pos = mouse.position

with open(config["char_file"], "r") as f:
    chars = json.loads(f.read())

CHARS_COUNT = len(chars["chars"])
CHARS_LIMIT = config["chat_chars_limit"]

FRAME_LIMIT = config["frame_record_limit"]

if os.path.exists(".minecraft/config/toughasnails/temperature.toml"):
    with open(".minecraft/config/toughasnails/temperature.toml", "r") as f:
        data = f.read()
    data = data.replace("climate_clemency_duration = 6000", "climate_clemency_duration = 0")
    with open(".minecraft/config/toughasnails/temperature.toml", "w") as f:
        f.write(data)

def clear_keyboard():
    for k in KEYS:
        handle_keyboard(k, False)

def clear_mouse():
    mouse.release(mbt.left)
    mouse.release(mbt.right)

def clear_all():
    clear_keyboard()
    clear_mouse()

def handle_keyboard(k, value):
    if value:
        pyautogui.keyDown(k)
    else:
        pyautogui.keyUp(k)

def handle_mouse(k, value):
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


def conv_char(char):
    data = np.zeros((CHARS_COUNT))
    for i in range(CHARS_COUNT):
        if chars["chars"][i] == char:
            data[i] = 1
    return data

def bin_to_char(bin):
    return chars["chars"][np.argmax(bin)]

def bin_to_name(bin):
    name = ""
    for b in bin:
        char = bin_to_char(b)
        if char != "\n":
            name += char
        else:
            break
    return name

def conv_name(name):
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

def drawPointer(img):
    draw = ImageDraw.Draw(img)
    pos = mouse.position
    draw.point(((pos[0]-int(screen.width/2-WIDTH/2), pos[1]-int(screen.height/2-HEIGHT/2))), fill=(255,0,0))
    return img

def getBit(value, bit):
    return value >> bit & 0b1

def convBit(value):
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

def send_learnData(hash_id):
    global learn_data, config, L_SERVER, SERVER
    if hash_id in learn_data:
        if len(learn_data[hash_id]) >= 2:
            try:
                headers = {
                    'content-type': 'video/mp4',
                    'id': hash_id
                }
                with open(os.path.join(WORK_DIR, "%s.mp4" % (hash_id)), "rb") as f:
                    requests.post("http://%s:%d/video" % (L_SERVER, PORT), data=f.read(), headers=headers)
                headers['content-type'] = 'application/json'
                sendData = {
                    "health": hp,
                    "data": learn_data[hash_id]
                }
                requests.post("http://%s:%d/" % (L_SERVER, PORT), json=sendData, headers=headers)
            except requests.exceptions.ConnectionError:
                res = requests.get("http://%s:%d/config?type=%s" % (CENTRAL_IP, 8000, SERV_TYPE))
                if res.status_code == 200:
                    config = json.loads(res.text)["config"]
                    L_SERVER = config["learn_server"]
                    SERVER = config["mc_server"]
        os.remove(os.path.join(WORK_DIR, "%s.mp4" % (hash_id)))
    files = os.listdir(WORK_DIR)
    for file in files:
        if file.endswith(".mp4"):
            os.remove(os.path.join(WORK_DIR, file))
    learn_data.clear()

def start_recording():
    global video
    global learn_data
    threading.Thread(target=download_update).start()
    hash_id = json.loads(requests.get('http://%s:%d/id' % (CENTRAL_IP, PORT)).text)["info"]["id"]
    fourcc = cv2.VideoWriter_fourcc('m','p','4','v')
    video = cv2.VideoWriter(os.path.join(WORK_DIR, "%s.mp4" % (hash_id)), fourcc, 10, (WIDTH, HEIGHT))
    learn_data[hash_id] = []
    return hash_id

def stop_recording(hash_id):
    global video
    video.release()
    threading.Thread(target=send_learnData, args=(hash_id,)).start()

def check_version():
    data = json.loads(requests.get("http://%s:%d/" % (L_SERVER, PORT)).text)
    current = int(data["version"])
    return current

def download_update():
    global DOWNLOAD_LOCK
    global AI_UPDATE_LOCK
    global VERSION
    modelFiles = ["model.h5", "vae_e.h5", "char_e.h5", "keyboard_d.h5", "mouse_d.h5"]
    if not DOWNLOAD_LOCK:
        DOWNLOAD_LOCK = True
        try:
            current = check_version()
            if current == 0:
                DOWNLOAD_LOCK = False
                for modelfile in modelFiles:
                    if os.path.exists(os.path.join(WORK_DIR, modelfile)):
                        os.remove(os.path.join(WORK_DIR, modelfile))
                os.remove(os.path.join(WORK_DIR, "version"))
                return
            if os.path.exists("version"):
                with open("version", "r") as f:
                    VERSION = int(f.read())
            if current > VERSION:
                logger.info("AI Model New Version Available!")
                for modelfile in modelFiles:
                    res = requests.get("http://%s:%d/%s" % (L_SERVER, PORT, modelfile))
                    with open(os.path.join(WORK_DIR, modelfile), "wb") as f:
                        f.write(res.content)
                while AI_USING:
                    sleep(0.1)
                AI_UPDATE_LOCK = True
                model.model.load_weights(os.path.join(WORK_DIR, "model.h5"))
                model.encoder.model.load_weights(os.path.join(WORK_DIR, "vae_e.h5"))
                model.charencoder.model.load_weights(os.path.join(WORK_DIR, "char_e.h5"))
                for c in model.nameencoder.chars:
                    c.model.load_weights(os.path.join(WORK_DIR, "char_e.h5"))
                model.keyboarddecoder.model.load_weights(os.path.join(WORK_DIR, "keyboard_d.h5"))
                model.mousedecoder.model.load_weights(os.path.join(WORK_DIR, "mouse_d.h5"))
                AI_UPDATE_LOCK = False
                VERSION = current
                with open("version", "w") as f:
                    f.write(str(VERSION))
                logger.info("AI Updated")
            DOWNLOAD_LOCK = False
        except:
            for modelfile in modelFiles:
                if os.path.exists(os.path.join(WORK_DIR, modelfile)):
                    os.remove(os.path.join(WORK_DIR, modelfile))
            if os.path.exists("version"):
                subprocess.run(["rm", "version"])
            AI_UPDATE_LOCK = False
            VERSION = 0
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
    logger.info("Send Chat to %s: %s" % (name, message))
    requests.get("http://localhost:%d/?name=%s&message=%s" % (PORT, name, message))

def send_chat_function(name, message):
    op_name = get_available_chat_name(name)
    if op_name != "":
        send_chat(op_name, urllib.parse.quote(message.replace("\n","").replace("\t","")))

def get_newName():
    while True:
        try:
            res = json.loads(requests.get("http://%s:%d/name?hostname=%s" % (CENTRAL_IP, PORT, HOSTNAME)).text)
            if res['status'] == 'ok':
                break
            register(True)
        except:
            pass
    return res["info"]["name"]

def end_session(hash_id):
    global model
    model.clearSession()
    gc.collect(2)
    clear_all()
    if hash_id in learn_data:
        stop_recording(hash_id)

def hostname2name(hostname):
    data = json.loads(requests.get('http://%s:%d/hostname?hostname=%s' % (CENTRAL_IP, PORT, hostname)).text)
    if data['status'] == 'ok':
        if data['info']['name'] != '':
            return data['info']['name']
    return "Dummy"

def force_quit():
    global FORCE_QUIT
    FORCE_QUIT = True
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

video = None

model = mcai.mcAI(WIDTH=WIDTH, HEIGHT=HEIGHT, CHARS_COUNT=CHARS_COUNT, logger=logger)
ptmc = PortableMinecraft(version=config["version"], name=HOSTNAME, resol="%dx%d" % (WIDTH, HEIGHT), server=SERVER)

learn_data = {}

if __name__ == "__main__":
    try:
        while True:
            mc_thread = threading.Thread(target=ptmc.start)
            mc_thread.start()
            while True:
                try:
                    requests.get("http://localhost:%d/" % (PORT))
                    break
                except:
                    sleep(0.1)
                    continue
            mc_start_time = time()
            mon = {'top': int(screen.height/2-HEIGHT/2), 'left': int(screen.width/2-WIDTH/2), 'width': WIDTH, 'height': HEIGHT}
            FORCE_QUIT = False
            played = False
            while True:
                get_newName()
                if FORCE_QUIT:
                    break
                send_message_data = ""
                random_seed = time()
                hash_id = start_recording()
                mem = np.random.random((2**8, 8))
                if os.path.exists(os.path.join(WORK_DIR, "model.h5")):
                    model.model.load_weights(os.path.join(WORK_DIR, "model.h5"))
                x, y = 0, 0
                mes_id = 0
                last = time()
                messages = []
                mem_reg, mem_reg2 = 0x0, 0x0
                char_at = 0
                hp = 0.0
                edit_char = ""
                inscreen = False
                before_key = [False for _ in KEYS]
                head_topbtm_time = -1
                last_pos, last_dir, last_change, last_change_pos = (-1, -1, -1), (-1, -1), -1, -1
                position_history = []
                newbie = True
                while True:
                    if not hash_id in learn_data:
                        learn_data[hash_id] = []
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
                            end_session(hash_id)
                            subprocess.run(["killall", "-9", "java"])
                            exit(10)
                    if data["screen"]:
                        if "net.minecraft.client.gui.screens.DisconnectedScreen" in data["screenInfo"]["id"]:
                            logger.warning("Disconnected. Auto restart...")
                            end_session(hash_id)
                            force_quit()
                            break
                    if data["playing"]:
                        played = True
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
                                data = json.loads(requests.get("http://%s:%d/effect?name=%s&clear=true&effect=toughasnails:climate_clemency" % (SERVER, PORT, HOSTNAME)).text)
                                sleep(0.1)
                                if data["status"] != "ok":
                                    logger.debug("Failed to clear effects")
                                    continue
                                for effect in effects:
                                    if random.random() < 0.01:
                                        level = int((random.random() ** 2) * 10)
                                        data = json.loads(requests.get("http://%s:%d/effect?name=%s&effect=%s&level=%d&duration=999999" % (SERVER, PORT, HOSTNAME, effect, level)).text)
                                        sleep(0.1)
                                        if data["status"] != "ok":
                                            logger.debug("Failed to add effect: %s" % (effect))
                                            continue
                                    break
                                break
                            newbie = False
                        if data["player"]["death"]:
                            logger.info("Dead")
                            end_session(hash_id)
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
                                if time() - head_topbtm_time >= 3 and len(learn_data[hash_id]) >= 2:
                                    logger.info("Head spinning")
                                    for _ in range(10):
                                        try:
                                            data = json.loads(requests.get("http://%s:%d/kill?name=%s" % (SERVER, PORT, HOSTNAME)).text)
                                            if data["status"] == "ok":
                                                sleep(1)
                                                break
                                        except:
                                            pass
                                        sleep(1)
                                    continue
                        else:
                            head_topbtm_time = -1
                        pos = (int(data["player"]["pos"]["x"]), int(data["player"]["pos"]["y"]), int(data["player"]["pos"]["z"]))
                        pos_float = (data["player"]["pos"]["x"], data["player"]["pos"]["y"], data["player"]["pos"]["z"])
                        dir = (int(data["player"]["direction"]["x"]), int(data["player"]["direction"]["y"]))
                        position_history.append(pos_float)
                        if len(position_history) > 1000:
                            position_history.pop(0)
                        average_pos = (0, 0, 0)
                        for p in position_history:
                            average_pos = (average_pos[0] + p[0], average_pos[1] + p[1], average_pos[2] + p[2])
                        average_pos = (average_pos[0] / len(position_history), average_pos[1] / len(position_history), average_pos[2] / len(position_history))
                        if pos_distance(average_pos, pos_float) <= 0.5 and len(position_history) >= 20:
                            if pos_distance(position_history[-1], position_history[-11]) <= 1 and len(learn_data[hash_id]) >= 2:
                                logger.info("No Walking")
                                for _ in range(10):
                                    try:
                                        data = json.loads(requests.get("http://%s:%d/kill?name=%s" % (SERVER, PORT, HOSTNAME)).text)
                                        if data["status"] == "ok":
                                            sleep(1)
                                            break
                                    except:
                                        pass
                                    sleep(1)
                                continue
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
                        ai_k, ai_m, ai_mem, ai_chat = model.predict(model.make_input(
                            x_img, x_reg, x_mem, x_reg2, x_mem2, x_name, x_mes, 1
                        ))
                        random.seed(random_seed)
                        ai_k += (np.random.random(ai_k.shape) * 2 - 1) * (random.random() ** 10)
                        for i in ai_m:
                            i += (np.random.random(i.shape) * 2 - 1) * (random.random() ** 10)
                        for i in ai_mem:
                            i += (np.random.random(i.shape) * 2 - 1) * (random.random() ** 10)
                        ai_chat += (np.random.random(ai_chat.shape) * 2 - 1) * (random.random() ** 10)
                        AI_USING = False
                        for i in range(len(KEYS)):
                            res = ai_k[0][i] >= 0.5
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
                        random.seed(time())
                        if random.random() < 0.1:
                            frame = cv2.cvtColor((x_img.reshape((HEIGHT,WIDTH,3))*255).astype("uint8"), cv2.COLOR_RGB2BGR)
                            video.write(frame)
                            this_frame = {
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
                            learn_data[hash_id].append(this_frame)
                        if not hash_id in learn_data:
                            hash_id = start_recording()
                        elif len(learn_data[hash_id]) > FRAME_LIMIT:
                            stop_recording(hash_id)
                            hash_id = start_recording()
                    else:
                        if played:
                            logger.warning("Logged out. Auto restart...")
                            end_session(hash_id)
                            force_quit()
                            break
                        elif time() - mc_start_time > 180:
                            logger.warning("Maybe disconnected. Auto restart...")
                            end_session(hash_id)
                            force_quit()
                            break
                    if len(data["message"]) > 0:
                        messages.append(data["message"][0])
                        logger.info("A message from " + data["message"][0]["author"] + " : " + data["message"][0]["message"])
                        mes_id = int(data["message"][0]["id"])
                    threading.Thread(target=register).start()
    finally:
        if not (hash_id == "" or hash_id == None):
            end_session(hash_id)
        force_quit()
