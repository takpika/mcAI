from math import sqrt
import subprocess, requests, json, pynput, screeninfo, urllib.parse, os, threading, random, pyautogui, hashlib, traceback
from mss import mss
from PIL import ImageDraw, Image
from time import sleep, time
import numpy as np

from pmc import PortableMinecraft
from GameSession import GameSession

from mcai.module import ModuleCore
from mcai.ai import Actor

class Client(ModuleCore):
    def __init__(self):
        super().__init__()
        self.HOSTNAME = hashlib.md5(os.uname()[1].encode()).hexdigest()[:16]
        self.getLogger()
        self.REGISTER_LAST_CHECK = 0
        self.sct = mss()
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
        self.PORT = self.config["port"]
        self.SERVER = self.config["mc_server"]
        self.L_SERVER = self.config["learn_server"]
        self.MC_FOLDER = self.config["mc_folder"]
        self.WORK_DIR = self.config["work_dir"]

        self.WIDTH = self.config["resolution"]["x"]
        self.HEIGHT = self.config["resolution"]["y"]

        self.AI_VERSION = 0
        self.AI_COUNT = 0
        self.AI_USING = False
        self.DOWNLOAD_LOCK = False
        self.AI_UPDATE_LOCK = False
        self.FORCE_QUIT = False

        vfp = os.path.join(self.WORK_DIR, "version.json")
        if os.path.exists(vfp):
            with open(vfp, "r") as f:
                version = json.loads(f.read())
                self.AI_VERSION = version["version"]
                self.AI_COUNT = version["count"]

        self.KEYS = ["q", "w", "e", "a", "s", "d", "shift", "space", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        pyautogui.PAUSE = 0.0

        self.effects = ["slowness", "blindness", "weakness", "poison", "wither"]

        self.screen = screeninfo.get_monitors()[0]
        self.mouse = pynput.mouse.Controller()
        self.mbt = pynput.mouse.Button
        self.mon = {'top': int(self.screen.height/2-self.HEIGHT/2), 'left': int(self.screen.width/2-self.WIDTH/2), 'width': self.WIDTH, 'height': self.HEIGHT}

        with open(self.config["char_file"], "r") as f:
            self.chars = json.loads(f.read())

        self.CHARS_COUNT: int = len(self.chars["chars"])
        self.CHARS_LIMIT: int = self.config["chat_chars_limit"]

        self.FRAME_LIMIT: int = self.config["frame_record_limit"]

        self.learn_data = {}
        self.videoFrames, self.videoFramePos = np.empty((self.FRAME_LIMIT, self.HEIGHT, self.WIDTH, 3), dtype="uint8"), 0
        self.model = Actor(WIDTH=self.WIDTH, HEIGHT=self.HEIGHT, CHARS_COUNT=self.CHARS_COUNT)
        self.actor = self.model.buildModel()
        self.ptmc = PortableMinecraft(version=self.config["version"], name=self.HOSTNAME, resol="%dx%d" % (self.WIDTH, self.HEIGHT), server=self.SERVER)

    def clear_keyboard(self):
        for k in self.KEYS:
            self.handle_keyboard(k, False)

    def clear_mouse(self):
        self.mouse.release(self.mbt.left)
        self.mouse.release(self.mbt.right)

    def clear_all(self):
        self.clear_keyboard()
        self.clear_mouse()

    def handle_keyboard(self, k: str, value: bool):
        if value:
            pyautogui.keyDown(k)
        else:
            pyautogui.keyUp(k)

    def handle_mouse(self, k: str, value: bool):
        if k == "left":
            if value:
                self.mouse.press(self.mbt.left)
            else:
                self.mouse.release(self.mbt.left)
        else:
            if value:
                self.mouse.press(self.mbt.right)
            else:
                self.mouse.release(self.mbt.right)

    def move_center(self):
        pos = self.mouse.position
        self.mouse.move(int(self.screen.width/2-pos[0]), int(self.screen.height/2-pos[1]))

    def check_mousecursor(self):
        pos = self.mouse.position
        if (pos[0] < self.screen.width/2-self.WIDTH/2) or pos[0] > self.screen.width/2+self.WIDTH/2:
            self.move_center()
        if (pos[1] < self.screen.height/2-self.HEIGHT/2) or pos[1] > self.screen.height/2+self.HEIGHT/2:
            self.move_center()

    def drawPointer(self, img: Image.Image):
        draw = ImageDraw.Draw(img)
        pos = self.mouse.position
        windowPos = (pos[0]-int(self.screen.width/2-self.WIDTH/2), pos[1]-int(self.screen.height/2-self.HEIGHT/2))
        draw.ellipse((windowPos[0]-2, windowPos[1]-2, windowPos[0]+2, windowPos[1]+2), fill=(255,0,0))
        return img

    def getBit(self, value: int, bit: int):
        return value >> bit & 0b1

    def convBit(self, value: np.ndarray) -> int:
        value = np.where(value < 0.5, 0, 1)
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

    def send_learnData(self, sessionID: str, endFramePos: int):
        if sessionID in self.learn_data:
            if len(self.learn_data[sessionID]) >= 2:
                try:
                    headers = {
                        'content-type': 'application/octet-stream',
                        'id': sessionID,
                        'width': str(self.WIDTH),
                        'height': str(self.HEIGHT),
                        'frameCount': str(endFramePos)
                    }
                    requests.post("http://%s:%d/videoND" % (self.L_SERVER, self.PORT), data=self.videoFrames[:endFramePos].tobytes(), headers=headers)
                    headers['content-type'] = 'application/json'
                    sendData = {
                        "data": self.learn_data[sessionID]
                    }
                    requests.post("http://%s:%d/" % (self.L_SERVER, self.PORT), json=sendData, headers=headers)
                except requests.exceptions.ConnectionError:
                    res = requests.get("http://%s:%d/config?type=%s" % (self.CENTRAL_IP, 8000, self.SERV_TYPE))
                    if res.status_code == 200:
                        self.config = json.loads(res.text)["config"]
                        self.L_SERVER = self.config["learn_server"]
                        self.SERVER = self.config["mc_server"]
        self.learn_data.clear()

    def startRecording(self) -> str:
        threading.Thread(target=self.download_update).start()
        sessionID = json.loads(requests.get('http://%s:%d/id' % (self.CENTRAL_IP, self.PORT)).text)["info"]["id"]
        self.videoFramePos = 0
        self.learn_data[sessionID] = []
        return sessionID

    def stopRecording(self, sessionID : str, endFramePos : int):
        threading.Thread(target=self.send_learnData, args=(sessionID, endFramePos)).start()

    def check_version(self):
        data = json.loads(requests.get("http://%s:%d/" % (self.L_SERVER, self.PORT)).text)
        current = data["version"]
        count = data["count"]
        return current, count

    def download_update(self):
        modelFiles = ["model.h5"]
        if not self.DOWNLOAD_LOCK:
            self.DOWNLOAD_LOCK = True
            try:
                currentVersion, currentCount = self.check_version()
                if currentVersion <= 0:
                    self.DOWNLOAD_LOCK = False
                    for modelfile in modelFiles:
                        if os.path.exists(os.path.join(self.WORK_DIR, modelfile)):
                            os.remove(os.path.join(self.WORK_DIR, modelfile))
                    if os.path.exists(os.path.join(self.WORK_DIR, "version.json")):
                        os.remove(os.path.join(self.WORK_DIR, "version.json"))
                    return
                if os.path.exists("version.json"):
                    with open("version.json", "r") as f:
                        versionData = json.loads(f.read())
                        self.AI_VERSION = versionData["version"]
                        self.AI_COUNT = versionData["count"]
                if currentVersion > self.AI_VERSION:
                    self.logger.info("AI Model New Version Available!")
                    for modelfile in modelFiles:
                        res = requests.get("http://%s:%d/%s" % (self.L_SERVER, self.PORT, modelfile))
                        with open(os.path.join(self.WORK_DIR, modelfile), "wb") as f:
                            f.write(res.content)
                    while self.AI_USING:
                        sleep(0.1)
                    self.AI_UPDATE_LOCK = True
                    self.actor.load_weights(os.path.join(self.WORK_DIR, "model.h5"))
                    self.AI_UPDATE_LOCK = False
                    self.AI_VERSION = currentVersion
                    self.AI_COUNT = currentCount
                    with open("version.json", "w") as f:
                        f.write(json.dumps({
                            "version": self.AI_VERSION,
                            "count": self.AI_COUNT
                        }))
                    self.logger.info("AI Updated")
                self.DOWNLOAD_LOCK = False
            except:
                for modelfile in modelFiles:
                    if os.path.exists(os.path.join(self.WORK_DIR, modelfile)):
                        os.remove(os.path.join(self.WORK_DIR, modelfile))
                if os.path.exists("version.json"):
                    subprocess.run(["rm", "version.json"])
                self.AI_UPDATE_LOCK = False
                self.AI_VERSION = 0
                self.AI_COUNT = 0
                self.DOWNLOAD_LOCK = False
                self.logger.error("AI Update Failed")

    def get_available_chat_name(self, name):
        res = requests.get("http://%s:%d/chat?hostname=%s" % (self.CENTRAL_IP, 8000, self.HOSTNAME))
        if res.status_code != 200:
            return ""
        else:
            data = json.loads(res.text)
            return data["info"]["name"]

    def send_chat(self, name, message):
        self.logger.info("Send Chat to %s: %s" % (name, message))
        requests.get("http://localhost:%d/?name=%s&message=%s" % (self.PORT, name, message))

    def send_chat_function(self, name, message):
        op_name = self.get_available_chat_name(name)
        if op_name != "":
            self.send_chat(op_name, urllib.parse.quote(message.replace("\n","").replace("\t","")))

    def get_newName(self) -> str:
        while True:
            try:
                res = json.loads(requests.get("http://%s:%d/name?hostname=%s" % (self.CENTRAL_IP, self.PORT, self.HOSTNAME)).text)
                if res['status'] == 'ok':
                    break
                self.register(ignore_time=True)
            except:
                pass
        return res["info"]["name"]

    def end_session(self, sessionID):
        self.clear_all()
        if sessionID in self.learn_data:
            self.stopRecording(sessionID, self.videoFramePos)

    def hostname2name(self, hostname):
        data = json.loads(requests.get('http://%s:%d/hostname?hostname=%s' % (self.CENTRAL_IP, self.PORT, hostname)).text)
        if data['status'] == 'ok':
            if data['info']['name'] != '':
                return data['info']['name']
        return "Dummy"

    def forceQuit(self):
        self.FORCE_QUIT = True
        self.logger.debug("Force Quit")
        try:
            while True:
                res = requests.get("http://localhost:%d/?close=true" % (self.PORT))
                if res.status_code > 0:
                    subprocess.run(["killall", "-9", "java"])
                else:
                    break
                sleep(1)
        except:
            exit(10)

    def pos_distance(self, pos1: tuple, pos2: tuple):
        return sqrt((pos1[0]-pos2[0])**2+(pos1[1]-pos2[1])**2+(pos1[2]-pos2[2])**2)

    def getModData(self, session: GameSession) -> dict:
        url = "http://localhost:%d/" % (self.PORT)
        send_data = {}
        if (session.moveDis[0] != 0 and not session.inScreen):
            send_data["x"] = float(session.moveDis[0])
        if (session.moveDis[1] != 0 and not session.inScreen):
            send_data["y"] = float(session.moveDis[1])
        if (session.checkedMesID > 0):
            send_data["checked"] = session.checkedMesID
        session.checkedMesID = 0
        failure = 0
        while True:
            try:
                if (len(list(send_data.keys())) > 0):
                    data = json.loads(requests.get("%s?%s" % (url, urllib.parse.urlencode(send_data))).text)
                else:
                    data = json.loads(requests.get(url).text)
                return data
            except:
                failure += 1
            if failure >= 10:
                self.logger.error("Connection Error")
                self.end_session(session.sessionID)
                subprocess.run(["killall", "-9", "java"])
                exit(10)

    def processScreen(self, data: dict, session: GameSession) -> bool:
        if "net.minecraft.client.gui.screens.DisconnectedScreen" in data["screenInfo"]["id"]:
            self.logger.warning("Disconnected. Auto restart...")
            self.end_session(session.sessionID)
            self.forceQuit()
            self.FORCE_QUIT = True
            return
        if data["screenInfo"]["pause"]:
            self.logger.info("Pause")
            pyautogui.keyDown("esc")
            sleep(0.2)
            pyautogui.keyUp("esc")
            return
        session.inScreen = True
        self.mouse.move(int(session.moveDis[0]), int(session.moveDis[1]))
        self.check_mousecursor()
        try:
            self.image = self.drawPointer(self.image)
        except:
            pass
        if data["screenInfo"]["edit"]:
            session.sendMessageData = ""
            char_k = None
            if session.editChar == "\n":
                char_k = "enter"
            elif session.editChar == "\t":
                char_k = "esc"
            elif session.editChar == "NONE":
                char_k = None
            elif session.editChar == "DEL":
                char_k = "backspace"
            else:
                char_k = session.editChar
            if char_k != None:
                pyautogui.keyDown(char_k)
                sleep(0.1)
                pyautogui.keyUp(char_k)

    def processDeath(self, session: GameSession):
        self.logger.info("Dead")
        if session.sessionID in self.learn_data:
            if len(self.learn_data[session.sessionID]) > 0:
                self.learn_data[session.sessionID][-1]["health"] = 0
        self.end_session(session.sessionID)
        for _ in range(100):
            data = self.getModData(session=session)
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
                self.logger.error("Failed to respawn")
                self.forceQuit()

    def processAI(self, data: dict, session: GameSession):
        x_img = np.array(self.image).reshape((1, self.HEIGHT, self.WIDTH, 3)) / 255
        x_reg = np.array([self.getBit(session.readMemRegs[0], i) for i in range(7,-1,-1)])
        x_mem = session.memory[session.readMemRegs[0]]
        x_reg2 = np.array([self.getBit(session.readMemRegs[1], i) for i in range(7,-1,-1)])
        x_mem2 = session.memory[session.readMemRegs[1]]
        if len(session.unreadMessages) > 0:
            if not "name" in session.unreadMessages[0]:
                session.unreadMessages[0]["name"] = self.hostname2name(session.unreadMessages[0]["author"])
            elif session.unreadMessages[0]["name"] == "":
                session.unreadMessages[0]["name"] = self.hostname2name(session.unreadMessages[0]["author"])
            x_name = self.convName(session.unreadMessages[0]["name"])
            x_mes = self.convChar(session.unreadMessages[0]["message"][char_at])
            char_at += 1
            if char_at >= len(session.unreadMessages[0]["message"]):
                char_at = 0
                session.unreadMessages.pop(0)
        else:
            x_name = self.convName("")
            x_mes = self.convChar("\t")
        while self.AI_UPDATE_LOCK:
            sleep(1)
            self.logger.info("Updating AI...")
        self.AI_USING = True
        ai_k, ai_m, ai_mem, ai_chat = self.actor.predict(self.model.make_input(
            x_img, x_reg, x_mem, x_reg2, x_mem2, x_name, x_mes, 1
        ), verbose=0)
        if random.random() < session.randomSeed:
            ai_k = np.random.random(ai_k.shape)
            ai_m[0] = np.random.random(ai_m[0].shape) * 2 - 1
            ai_m[1] = np.random.random(ai_m[1].shape)
            for i in ai_mem:
                i = np.random.random(i.shape)
            ai_chat = np.random.random(ai_chat.shape)
        self.AI_USING = False
        ai_k = np.where(ai_k < 0.5, 0, 1)
        ai_m[0] = np.clip(ai_m[0], -1, 1)
        ai_m[1] = np.where(ai_m[1] < 0.5, 0, 1)
        for i in range(len(ai_mem)):
            if i == 1:
                ai_mem[i] = np.clip(ai_mem[i], 0, 1)
            ai_mem[i] = np.where(ai_mem[i] < 0.5, 0, 1)
        ai_chat = np.where(ai_chat == np.max(ai_chat), 1, 0)
        for i in range(len(self.KEYS)):
            res = ai_k[0][i] >= 0.5
            if res and self.KEYS[i] == "space":
                session.jumpCount += 1
            if session.beforeKeys[i] != res:
                self.handle_keyboard(self.KEYS[i], ai_k[0][i] >= 0.5)
            session.beforeKeys[i] = res
        for i in range(2): session.moveDis[i] = ai_m[0][0][i] * 20
        self.handle_mouse("left", ai_m[1][0][0] >= 0.5)
        self.handle_mouse("right", ai_m[1][0][1] >= 0.5)
        save_reg = self.convBit(ai_mem[0][0])
        session.memory[save_reg] = ai_mem[1][0]
        session.readMemRegs[0] = self.convBit(ai_mem[2][0])
        session.readMemRegs[1] = self.convBit(ai_mem[3][0])
        mes_char = self.bin2Char(ai_chat[0])
        if mes_char != "\n" and mes_char != "NONE" and not data["screen"]:
            if mes_char == "DEL":
                if len(session.sendMessageData) > 1:
                    session.sendMessageData = session.sendMessageData[:-1]
                else:
                    session.sendMessageData = ""
            elif mes_char == "\t":
                threading.Thread(target=self.send_chat_function, args=(data["player"]["name"], session.sendMessageData)).start()
                session.sendMessageData = ""
            else:
                session.sendMessageData += mes_char
        elif data["screen"]:
            if data["screenInfo"]["edit"]:
                session.editChar = mes_char
        if len(session.sendMessageData) > self.CHARS_LIMIT:
            session.sendMessageData = session.sendMessageData[:self.CHARS_LIMIT]
        if random.random() < 0.1:
            self.videoFrames[self.videoFramePos] = (x_img.reshape((self.HEIGHT,self.WIDTH,3))*255).astype("uint8")
            self.videoFramePos += 1
            this_frame = {
                "health": data["player"]["health"],
                "input": {
                    "mem": {
                        "reg": self.convBit(x_reg),
                        "data": x_mem.tolist(),
                        "reg2": self.convBit(x_reg2),
                        "data2": x_mem2.tolist()
                    },
                    "chat": {
                        "name": self.bin2Name(x_name),
                        "message": self.bin2Char(x_mes)
                    }
                }, 
                "output": {
                    "keyboard": ai_k[0].tolist(),
                    "mouse": {
                        "dir": ai_m[0][0].tolist(),
                        "button": ai_m[1][0].tolist()
                    } ,
                    "mem": {
                        "save": self.convBit(ai_mem[0][0]),
                        "mem": ai_mem[1][0].tolist(),
                        "reg": self.convBit(ai_mem[2][0]),
                        "reg2": self.convBit(ai_mem[3][0])
                    },
                    "chat": self.bin2Char(ai_chat[0])
                }
            }
            self.learn_data[session.sessionID].append(this_frame)

    def changeGameMode(self, mode: str):
        for _ in range(10):
            try:
                data = json.loads(requests.get("http://%s:%d/gamemode?name=%s&mode=%s" % (self.SERVER, self.PORT, self.HOSTNAME, mode.lower())).text)
                if data["status"] == "ok":
                    break
                sleep(0.1)
            except:
                pass
        sleep(1)

    def giveEffect(self, playerName: str, effectName: str, level: int, duration: int) -> bool:
        result = json.loads(requests.get("http://%s:%d/effect?name=%s&effect=%s&level=%d&duration=%d" % (self.SERVER, self.PORT, playerName, effectName, level, duration)).text) # before: 255 3 sec
        if result["status"] != "ok":
            self.logger.debug("Failed to add effect: %s" % (effectName))
        return result["status"] == "ok"
    
    def clearEffect(self, playerName: str) -> bool:
        result = json.loads(requests.get("http://%s:%d/effect?name=%s&clear=true" % (self.SERVER, self.PORT, playerName)).text)
        if result["status"] != "ok":
            self.logger.debug("Failed to clear effects")
        return result["status"] == "ok"

    def tick(self, session: GameSession):
        if not self.ptmc.running:
            self.FORCE_QUIT = True
            return
        if not session.sessionID in self.learn_data:
            self.learn_data[session.sessionID] = []
        data = self.getModData(session=session)
        if data["screen"]:
            self.processScreen(data=data, session=session)
            if self.FORCE_QUIT: return
        if data["playing"]:
            self.played = True
            FPS = -1
            img = self.sct.grab(self.mon)
            self.image = Image.frombytes('RGB', (img.width, img.height), img.rgb)
            if data["player"]["gamemode"] != "SURVIVAL":
                self.changeGameMode("survival")
                return
            if session.newbie:
                for _ in range(10):
                    self.clearEffect(self.HOSTNAME)
                    if not self.giveEffect(self.HOSTNAME, "hunger", 255, 2):
                        return
                    session.nextHunger += 120
                    if not self.giveEffect(self.HOSTNAME, "strength", 0, 999999):
                        return
                    for effect in self.effects:
                        if random.random() < 0.01:
                            level = int((random.random() ** 2) * 10)
                            self.giveEffect(self.HOSTNAME, effect, level, 999999)
                    break
                session.newbie = False
            if session.newbieDamage and not session.newbieDamageChecked:
                if data["player"]["health"] <= 8:
                    session.newbieDamageChecked = True
                else:
                    session.newbieDamage = False
            if data["player"]["health"] > 8 and not session.newbieDamage:
                if self.giveEffect(self.HOSTNAME, "instant_damage", 1, 1):
                    session.newbieDamage = True
                    sleep(1)
                return
            if session.playStartTime == -1:
                session.playStartTime = time()
            session.playFrameCounts += 1
            FPS = session.playFrameCounts / (time() - session.playStartTime)
            if time() > session.nextHunger or session.jumpCount >= FPS * 10:
                if session.jumpCount >= FPS * 10:
                    session.jumpCount = 0
                if self.giveEffect(self.HOSTNAME, "hunger", 39, 1) and time() > session.nextHunger:
                    session.nextHunger += 120
            if data["player"]["health"] <= session.beforeHp - 10:
                session.criticalHp = data["player"]["health"] + 5
                self.giveEffect(self.HOSTNAME, "slowness", 5, 3600)
                self.giveEffect(self.HOSTNAME, "mining_fatigue", 1, 3600)
                self.giveEffect(self.HOSTNAME, "weakness", 0, 3600)
                self.giveEffect(self.HOSTNAME, "jump_boost", 254, 3600)
            if data["player"]["health"] >= session.criticalHp:
                self.clearEffect(self.HOSTNAME)
                session.criticalHp = 999999
            session.beforeHp = data["player"]["health"]
            if data["player"]["death"]:
                self.processDeath(session=session)
                return
            if data["screen"]:
                self.processScreen(data=data, session=session)
            else:
                session.inScreen = False
            dir_X = data["player"]["direction"]["x"]
            if dir_X < 0:
                dir_X *= -1
            if dir_X > 80:
                if session.headTopBtmTime == -1:
                    session.headTopBtmTime = time()
                else:
                    if time() - session.headTopBtmTime >= 3 and len(self.learn_data[session.sessionID]) >= 2 and not session.headProcessed:
                        self.logger.info("Head spinning")
                        self.giveEffect(self.HOSTNAME, "hunger", 255, 60)
                        session.headProcessed = True
            else:
                session.headTopBtmTime = -1
                session.headProcessed = False
            pos_float = (data["player"]["pos"]["x"], data["player"]["pos"]["y"], data["player"]["pos"]["z"])
            session.positionHistory.append(pos_float)
            if len(session.positionHistory) > FPS * 60 * 60:
                session.positionHistory.pop(0)
            average_pos = (0, 0, 0)
            for p in session.positionHistory:
                average_pos = (average_pos[0] + p[0], average_pos[1] + p[1], average_pos[2] + p[2])
            average_pos = (average_pos[0] / len(session.positionHistory), average_pos[1] / len(session.positionHistory), average_pos[2] / len(session.positionHistory))
            if self.pos_distance(average_pos, pos_float) <= min(len(session.positionHistory)/FPS*0.01, 10):
                if session.afkStartTime == -1:
                    session.afkStartTime = time()
                else:
                    if time() - session.afkStartTime >= 5 and not session.afkProcessed:
                        self.logger.info("AFK")
                        self.giveEffect(self.HOSTNAME, "hunger", 255, 60)
                        session.afkProcessed = True
            else:
                session.afkStartTime = -1
                session.afkProcessed = False
            self.processAI(data=data, session=session)
            if not session.sessionID in self.learn_data:
                session.sessionID = self.startRecording()
            elif len(self.learn_data[session.sessionID]) > self.FRAME_LIMIT:
                self.stopRecording(session.sessionID)
                session.sessionID = self.startRecording()
        else:
            if self.played:
                self.logger.warning("Logged out. Auto restart...")
                self.end_session(session.sessionID)
                self.forceQuit()
            elif time() - self.mcStartTime > 180:
                self.logger.warning("Maybe disconnected. Auto restart...")
                self.end_session(session.sessionID)
                self.forceQuit()
        if len(data["message"]) > 0:
            session.unreadMessages.append(data["message"][0])
            self.logger.info("A message from " + data["message"][0]["author"] + " : " + data["message"][0]["message"])
            session.checkedMesID = int(data["message"][0]["id"])
        threading.Thread(target=self.register).start()

    def playSession(self):
        self.get_newName()
        self.session = GameSession(sessionID=self.startRecording(), parent=self)
        if os.path.exists(os.path.join(self.WORK_DIR, "model.h5")):
            self.actor.load_weights(os.path.join(self.WORK_DIR, "model.h5"))
        while True:
            if self.FORCE_QUIT: return
            self.tick(session=self.session)

    def gameSession(self):
        mc_thread = threading.Thread(target=self.ptmc.start)
        mc_thread.start()
        sleep(0.1)
        while True:
            if not self.ptmc.running: break
            try:
                requests.get("http://localhost:%d/" % (self.PORT))
                break
            except:
                sleep(0.1)
                continue
        if not self.ptmc.running: return
        self.mcStartTime = time()
        self.FORCE_QUIT = False
        self.played = False
        while True:
            if self.FORCE_QUIT: break
            self.playSession()

    def startGame(self):
        try:
            while True: self.gameSession()
        except Exception as e:
            t = list(traceback.TracebackException.from_exception(e).format())
            for i in t:
                self.logger.error(i)
        finally:
            try:
                self.end_session(self.session.sessionID)
            except:
                pass
            self.forceQuit()

    def start(self):
        self.startGame()

if __name__ == "__main__":
    client = Client()
    client.start()
