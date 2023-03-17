from http.server import HTTPServer, BaseHTTPRequestHandler
import shutil
from socketserver import ThreadingMixIn
import threading
import json, mcai, argparse, os, psutil, socket, requests, subprocess, random, pickle, cv2, shutil, time
from time import sleep
import numpy as np
from datetime import datetime
from logging import getLogger, DEBUG, StreamHandler, Formatter
from PIL import Image
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input

logger = getLogger(__name__)
logger.setLevel(DEBUG)
logger_handler = StreamHandler()
logger_formatter = Formatter(fmt='%(asctime)-15s [%(name)s] %(message)s')
logger_handler.setFormatter(logger_formatter)
logger.addHandler(logger_handler)

SERV_TYPE = "learn"

CENTRAL_IP = None
GPU_AVAIL = tf.test.is_gpu_available()

if not os.path.exists("models/"):
    os.mkdir("models")

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
    sock.settimeout(3)
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

for key in config.keys():
    if type(config[key]) == str:
        config[key] = config[key].replace("__HOME__", os.getenv('HOME'))
        config[key] = config[key].replace("__WORKDIR__", os.getcwd())

SAVE_FOLDER = config["save_folder"]
DATA_FOLDER = config["data_folder"]
if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

WIDTH = config["resolution"]["x"]
HEIGHT = config["resolution"]["y"]

EPOCHS = config["epochs"]

with open(config["char_file"], "r") as f:
    chars = json.loads(f.read())

CHARS_COUNT = len(chars["chars"])
LEARN_LIMIT = 1000
USE_LEARN_LIMIT = 3

data = []
learn_data = []
TRAINING = False
vae = mcai.image.ImageVAE()
charVAE = mcai.text.CharVAE(CHARS_COUNT)
keyboardVAE = mcai.control.KeyboardVAE()
mouseVAE = mcai.control.MouseVAE()
actor = mcai.Actor(WIDTH=WIDTH, HEIGHT=HEIGHT, CHARS_COUNT=CHARS_COUNT, logger=logger)
critic = mcai.Critic(WIDTH=WIDTH, HEIGHT=HEIGHT, CHARS_COUNT=CHARS_COUNT, logger=logger)
critic.model.trainable = False
imgIn = Input(shape=(256, 256, 3))
regIn = Input(shape=(8))
memIn = Input(shape=(8))
reg2In = Input(shape=(8))
mem2In = Input(shape=(8))
nameIn = [Input(shape=(CHARS_COUNT)) for _ in range(6)]
mesIn = Input(shape=(CHARS_COUNT))
seedIn = Input(shape=(100))
actorAction = actor.model([imgIn, [regIn, memIn, reg2In, mem2In], [nameIn, mesIn], seedIn])
valid = critic.model([[imgIn, [regIn, memIn, reg2In, mem2In], [nameIn, mesIn]], actorAction])
combined = Model(inputs=[imgIn, [regIn, memIn, reg2In, mem2In], [nameIn, mesIn], seedIn], outputs=[valid])
combined.compile(loss="mse", optimizer="Adam")

def limit(i):
    i[i>1]=1
    i[i<0]=0
    return i

def nichi(i):
    i[i>=0.5]=1
    i[i<0.5]=0
    return i

def convAll():
    global learn_data
    learnDataLength = len(learn_data)
    x_img = np.empty((learnDataLength, HEIGHT, WIDTH, 3))
    x_reg = np.empty((learnDataLength, 8))
    x_mem = np.empty((learnDataLength, 8))
    x_reg2 = np.empty((learnDataLength, 8))
    x_mem2 = np.empty((learnDataLength, 8))
    x_name = np.empty((learnDataLength, 6, CHARS_COUNT))
    x_mes = np.empty((learnDataLength, CHARS_COUNT))
    ai_k = np.empty((learnDataLength, 17))
    ai_m_1 = np.empty((learnDataLength, 2))
    ai_m_2 = np.empty((learnDataLength, 2))
    ai_mem_1 = np.empty((learnDataLength, 8))
    ai_mem_2 = np.empty((learnDataLength, 8))
    ai_mem_3 = np.empty((learnDataLength, 8))
    ai_mem_4 = np.empty((learnDataLength, 8))
    ai_chat = np.empty((learnDataLength, CHARS_COUNT))
    for i in range(learnDataLength):
        x_img[i] = learn_data[i][0].reshape((HEIGHT,WIDTH,3))
        x_reg[i] = learn_data[i][1].reshape((8))
        x_mem[i] = learn_data[i][2].reshape((8))
        x_reg2[i] = learn_data[i][3].reshape((8))
        x_mem2[i] = learn_data[i][4].reshape((8))
        x_name[i] = learn_data[i][5].reshape((6, CHARS_COUNT))
        x_mes[i] = learn_data[i][6].reshape((CHARS_COUNT))
        ai_k[i] = learn_data[i][7].reshape((17))
        ai_m_1[i] = learn_data[i][8].reshape((2))
        ai_m_2[i] = learn_data[i][9].reshape((2))
        ai_mem_1[i] = learn_data[i][10].reshape((8))
        ai_mem_2[i] = learn_data[i][11].reshape((8))
        ai_mem_3[i] = learn_data[i][12].reshape((8))
        ai_mem_4[i] = learn_data[i][13].reshape((8))
        ai_chat[i] = learn_data[i][14].reshape((CHARS_COUNT))
    ai_k = np.clip(ai_k, 0, 1)
    ai_m_1 = np.clip(ai_m_1, -1, 1)
    ai_m_2 = np.clip(ai_m_2, 0, 1)
    ai_mem_1 = np.where(ai_mem_1<0.5, 0, 1)
    ai_mem_2 = np.where(ai_mem_2<0.5, 0, 1)
    ai_mem_3 = np.where(ai_mem_3<0.5, 0, 1)
    ai_mem_4 = np.where(ai_mem_4<0.5, 0, 1)
    ai_chat = np.clip(ai_chat, 0, 1)
    input_data = actor.make_input(
        x_img, x_reg, x_mem, x_reg2, x_mem2, np.transpose(x_name, (1,0,2)), x_mes, x_img.shape[0]
    )
    output_data = [
        ai_k, [ai_m_1, ai_m_2], [ai_mem_1, ai_mem_2, ai_mem_3, ai_mem_4], ai_chat
    ]
    learn_data.clear()
    return input_data, output_data

def conv_frame(ld):
    inpdata = []
    inpdata.append(np.array([convBit(ld["input"]["mem"]["reg"])]))
    inpdata.append(np.array([ld["input"]["mem"]["data"]]))
    inpdata.append(np.array([convBit(ld["input"]["mem"]["reg2"])]))
    inpdata.append(np.array([ld["input"]["mem"]["data2"]]))
    inpdata.append(np.array([conv_name(ld["input"]["chat"]["name"])]))
    inpdata.append(np.array([conv_char(ld["input"]["chat"]["message"])]))
    inpdata.append(np.array([ld["output"]["keyboard"]]))
    inpdata.append(np.array([ld["output"]["mouse"]["dir"]]))
    inpdata.append(np.array([ld["output"]["mouse"]["button"]]))
    inpdata.append(np.array([convBit(ld["output"]["mem"]["save"])]))
    inpdata.append(np.array([ld["output"]["mem"]["mem"]]))
    inpdata.append(np.array([convBit(ld["output"]["mem"]["reg"])]))
    inpdata.append(np.array([convBit(ld["output"]["mem"]["reg2"])]))
    inpdata.append(np.array([conv_char(ld["output"]["chat"])]))
    return inpdata

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

def getBit(value, bit):
    return value >> bit & 0b1

def convBit(value):
    return np.array([getBit(value, i) for i in range(7, -1, -1)])

CHECK_PROCESSING = False
MODEL_WRITING = False
CHECK_FIRSTRUN = True

def checkCount():
    learn_list_ids = [file.replace(".mp4","").replace(".pkl","") for file in os.listdir(DATA_FOLDER)]
    learn_ids = [id for id in set(learn_list_ids) if learn_list_ids.count(id) == 2]
    learn_frames = [len(pickle.load(open(os.path.join(DATA_FOLDER, "%s.pkl" % (id)), "rb"))["data"]) for id in learn_ids]
    learn_counts = [pickle.load(open(os.path.join(DATA_FOLDER, "%s.pkl" % (id)), "rb"))["count"] for id in learn_ids]
    rewards = [pickle.load(open(os.path.join(DATA_FOLDER, "%s.pkl" % (id)), "rb"))["reward"] for id in learn_ids]
    return learn_ids, learn_frames, learn_counts, rewards

def check():
    global data
    global CHECK_PROCESSING, CHECK_FIRSTRUN, LEARN_LIMIT, TRAINING
    list_ids = [file.replace(".mp4","").replace(".json","") for file in os.listdir(SAVE_FOLDER)]
    ids = [id for id in set(list_ids) if list_ids.count(id) == 2]
    learn_frames = [0]
    if len(ids) >= 10 and not CHECK_PROCESSING and not TRAINING:
        CHECK_PROCESSING = True
        counts = []
        ids_copy = ids.copy()
        for i in range(len(ids)):
            id = ids[i]
            try:
                count = len(json.loads(open(os.path.join(SAVE_FOLDER, "%s.json" % (id)), "r").read())["data"])
                if count >= 2:
                    counts.append(count)
                    continue
            except:
                pass
            os.remove(os.path.join(SAVE_FOLDER, "%s.mp4" % (id)))
            os.remove(os.path.join(SAVE_FOLDER, "%s.json" % (id)))
            ids_copy.remove(id)
        ids = ids_copy.copy()
        if len(counts) > 0:
            for id in ids:
                shutil.move(os.path.join(SAVE_FOLDER, "%s.mp4" % (id)), os.path.join(DATA_FOLDER, "%s.mp4" % (id)))
                shutil.move(os.path.join(SAVE_FOLDER, "%s.json" % (id)), os.path.join(DATA_FOLDER, "%s.json" % (id)))
                with open(os.path.join(DATA_FOLDER, "%s.json" % (id)), "r") as f:
                    data = json.loads(f.read())
                c_data = []
                reward = 0.0
                for i in range(len(data["data"])):
                    daf = conv_frame(data["data"][i])
                    c_data.append(daf)
                    reward += data["data"][i]["health"] * ( 0.999 ** i )
                allData = {
                    "count": 0,
                    "reward": reward,
                    "data": c_data
                }
                with open(os.path.join(DATA_FOLDER, "%s.pkl" % (id)), "wb") as f:
                    pickle.dump(allData, f)
                os.remove(os.path.join(DATA_FOLDER, "%s.json" % (id)))
        learn_ids, learn_frames, learn_counts, rewards = checkCount()
        CHECK_FIRSTRUN = False
        logger.debug("Check done, current total frames: %d/%d" % (sum(learn_frames), LEARN_LIMIT))
        CHECK_PROCESSING = False
    if CHECK_FIRSTRUN:
        learn_ids, learn_frames, learn_counts, rewards = checkCount()
        logger.debug("First Run, current total frames: %d" % (sum(learn_frames)))
        CHECK_FIRSTRUN = False
        TRAINING = True
        if not os.path.exists("models/char_e.h5") or not os.path.exists("models/char_d.h5"):
            charVAELearn()
        if not os.path.exists("models/keyboard_e.h5") or not os.path.exists("models/keyboard_d.h5"):
            keyboardVAELearn()
        if not os.path.exists("models/mouse_e.h5") or not os.path.exists("models/mouse_d.h5"):
            mouseVAELearn()
        TRAINING = False
    if sum(learn_frames) >= LEARN_LIMIT and not TRAINING:
        learn(learn_ids, learn_frames, learn_counts, rewards)

def learn(learn_ids: list, learn_frames: list[int], learn_counts: list, rewards: list):
    global LEARN_LIMIT, TRAINING, MODEL_WRITING
    global model, vae
    batchSize = 32
    if TRAINING:
        return
    TRAINING = True
    logger.info("Start Learning")
    mx = max(learn_frames)
    ave = sum(learn_frames) / len(learn_frames)
    beforeLimit = LEARN_LIMIT
    LEARN_LIMIT = min(mx * 100, 1000)
    if LEARN_LIMIT != beforeLimit:
        logger.debug("Learn Limit has Changed: %d" % (LEARN_LIMIT))
    logger.debug("Start: Image VAE Learning")
    if os.path.exists("models/vae_d_latest.h5") and os.path.exists("models/vae_e_latest.h5"):
        vae.decoder.model.load_weights("models/vae_d_latest.h5")
        vae.encoder.model.load_weights("models/vae_e_latest.h5")
    video_ids = [file.replace(".mp4", "") for file in os.listdir(DATA_FOLDER) if ".mp4" in file.lower() and file[0] != "."]
    if sum(learn_frames) <= 10000:
        logger.debug("Start: Image VAE Learning (Small Data)")
        vaeFrames = np.empty((sum(learn_frames), 256, 256, 3), dtype=np.uint8)
        i = 0
        for id in video_ids:
            video = cv2.VideoCapture(os.path.join(DATA_FOLDER, "%s.mp4" % (id)))
            while True:
                ret, frame = video.read()
                if not ret:
                    video.release()
                    break
                try:
                    frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((256, 256))
                    vaeFrames[i] = np.array(frame)
                    i += 1
                except:
                    pass
        iters = i // batchSize
        for epoch in range(2):
            for iter in range(iters):
                loss = vae.model.train_on_batch(vaeFrames[iter*batchSize:(iter+1)*batchSize]/255, vaeFrames[iter*batchSize:(iter+1)*batchSize]/255)
                if iter % 10 == 0:
                    logger.debug("Image VAE Loss: %.6f, %d epochs, %d iters" % (loss, epoch, iter))
    else:
        logger.debug("Start: Image VAE Learning (Large Data)")
        vaeFrames = np.empty((batchSize, 256, 256, 3), dtype=np.uint8)
        for epoch in range(2):
            i = 0
            iter = 0
            video = cv2.VideoCapture(os.path.join(DATA_FOLDER, "%s.mp4" % (video_ids[i])))
            framesCount = 0
            while True:
                ret, frame = video.read()
                if not ret:
                    video.release()
                    if i < len(video_ids) - 1:
                        i += 1
                        video = cv2.VideoCapture(os.path.join(DATA_FOLDER, "%s.mp4" % (video_ids[i])))
                        continue
                    else:
                        vae.model.train_on_batch(vaeFrames[0:framesCount]/255, vaeFrames[0:framesCount]/255)
                        framesCount = 0
                        break
                try:
                    frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((256,256))
                    vaeFrames[framesCount] = np.array(frame).astype("uint8").reshape(256,256,3)
                    framesCount += 1
                except:
                    logger.warning("Frame Skipped")
                    logger.warning(frame)
                if framesCount >= batchSize:
                    iter += 1
                    framesCount = 0
                    loss = vae.model.train_on_batch(vaeFrames/255, vaeFrames/255)
                    if iter % 10 == 0:
                        logger.debug("Image VAE Loss: %.6f, %d epochs, %3d" % (loss, epoch, iter))
    del vaeFrames
    vae.encoder.model.save("models/vae_e_latest.h5")
    vae.decoder.model.save("models/vae_d_latest.h5")
    vaeOverride = random.random() < 0.01
    if not os.path.exists("models/vae_e.h5") or not os.path.exists("models/vae_d.h5") or vaeOverride:
        logger.debug("Image VAE Model Updated")
        shutil.copy("models/vae_e_latest.h5", "models/vae_e.h5")
        shutil.copy("models/vae_d_latest.h5", "models/vae_d.h5")
    mcai.clearSession()
    logger.debug("End: Image VAE Learning")
    mx = max(rewards)
    this_epochs = EPOCHS if not vaeOverride else 500
    actor.encoder.model.load_weights("models/vae_e.h5")
    actor.charencoder.model.load_weights("models/char_e.h5")
    for c in actor.nameencoder.chars:
        c.model.load_weights("models/char_e.h5")
    actor.keyboarddecoder.model.load_weights("models/keyboard_d.h5")
    actor.mousedecoder.model.load_weights("models/mouse_d.h5")
    critic.encoder.model.load_weights("models/vae_e.h5")
    critic.charencoder.model.load_weights("models/char_e.h5")
    for c in critic.nameencoder.chars:
        c.model.load_weights("models/char_e.h5")
    critic.keyboardencoder.model.load_weights("models/keyboard_e.h5")
    critic.mouseencoder.model.load_weights("models/mouse_e.h5")
    critic.actorcharencoder.model.load_weights("models/char_e.h5")
    logger.debug("Start: Critic Learning")
    maxRewardAve = 0
    for epoch in range(this_epochs):
        loss_history = []
        for i in range(len(learn_ids)):
            with open(os.path.join(DATA_FOLDER, "%s.pkl" % (learn_ids[i])), "rb") as f:
                data = pickle.load(f)
            video = cv2.VideoCapture(os.path.join(DATA_FOLDER, "%s.mp4" % (learn_ids[i])))
            rewardAve = rewards[i] / len(data["data"])
            maxRewardAve = max(maxRewardAve, rewardAve)
            for frame in data["data"]:
                ret, frameImg = video.read()
                frameData = []
                if not ret:
                    break
                frameImg = Image.fromarray(cv2.cvtColor(frameImg, cv2.COLOR_BGR2RGB)).resize((256, 256))
                frameImg = np.array(frameImg).astype("uint8").reshape(1, 256, 256, 3) / 255
                frameData.append(frameImg)
                frameData.extend(frame)
                learn_data.append(frameData)
            video.release()
            x, y = convAll()
            x = x[:-1]
            x.extend(y)
            y = np.array([rewardAve for _ in range(len(data["data"]))])
            loss = critic.model.train_on_batch(x, y)
            loss_history.append(loss)
        logger.info("Critic Loss: %.6f, %d epochs" % (sum(loss_history)/len(loss_history), epoch))
    logger.debug("End: Critic Learning")
    logger.debug("Start: Actor Learning")
    for epoch in range(this_epochs):
        loss_history = []
        for i in range(len(learn_ids)):
            with open(os.path.join(DATA_FOLDER, "%s.pkl" % (learn_ids[i])), "rb") as f:
                data = pickle.load(f)
            video = cv2.VideoCapture(os.path.join(DATA_FOLDER, "%s.mp4" % (learn_ids[i])))
            rewardAve = rewards[i] / len(data["data"])
            for frame in data["data"]:
                ret, frameImg = video.read()
                frameData = []
                if not ret:
                    break
                frameImg = Image.fromarray(cv2.cvtColor(frameImg, cv2.COLOR_BGR2RGB)).resize((256, 256))
                frameImg = np.array(frameImg).astype("uint8").reshape(1, 256, 256, 3) / 255
                frameData.append(frameImg)
                frameData.extend(frame)
                frameData.append(rewardAve)
                learn_data.append(frameData)
            video.release()
            x, _ = convAll()
            y = np.array([maxRewardAve for _ in range(len(data["data"]))])
            loss = combined.train_on_batch(x, y)
            loss_history.append(loss)
        logger.info("Actor Loss: %.6f, %d epochs" % (sum(loss_history)/len(loss_history), epoch))
    logger.debug("End: Actor Learning")
    for id in learn_ids:
        os.remove(os.path.join(DATA_FOLDER, "%s.pkl" % (id)))
        os.remove(os.path.join(DATA_FOLDER, "%s.mp4" % (id)))
    logger.info("Finish Learning")
    MODEL_WRITING = True
    actor.model.save("models/model.h5")
    MODEL_WRITING = False
    mcai.clearSession()
    version = {
        "version": time.time(),
        "count": 1
    }
    if os.path.exists("models/version.json"):
        with open("models/version.json", "r") as f:
            beforeVersion = json.load(f)
        if "count" in beforeVersion:
            version["count"] = beforeVersion["count"] + 1
    with open("models/version.json", "w") as f:
        json.dump(version, f)
    TRAINING = False

def charVAELearn():
    logger.debug("Start: Char VAE Learning")
    for epoch in range(100000):
        x = np.random.random((100, CHARS_COUNT))
        x = np.where(x == x.max(axis=1, keepdims=True), 1, 0)
        loss = charVAE.model.train_on_batch(x, x)
        if epoch % 1000 == 0:
            logger.debug("Char VAE Loss: %.6f, %d epochs" % (loss, epoch))
    charVAE.encoder.model.save("models/char_e.h5")
    charVAE.decoder.model.save("models/char_d.h5")
    mcai.clearSession()
    logger.debug("End: Char VAE Learning")

def keyboardVAELearn():
    logger.debug("Start: Keyboard VAE Learning")
    for epoch in range(100000):
        x = np.random.random((100, 17))
        x = np.where(x >= 0.5, 1, 0)
        loss = keyboardVAE.model.train_on_batch(x, x)
        if epoch % 1000 == 0:
            logger.debug("Keyboard VAE Loss: %.6f, %d epochs" % (loss, epoch))
    keyboardVAE.encoder.model.save("models/keyboard_e.h5")
    keyboardVAE.decoder.model.save("models/keyboard_d.h5")
    mcai.clearSession()
    logger.debug("End: Keyboard VAE Learning")

def mouseVAELearn():
    logger.debug("Start: Mouse VAE Learning")
    for epoch in range(100000):
        x_dir = np.random.random((100, 2)) * 2 - 1
        x_btn = np.random.random((100, 2))
        x_btn = np.where(x_btn >= 0.5, 1, 0)
        loss = mouseVAE.model.train_on_batch([x_dir, x_btn], [x_dir, x_btn])
        if epoch % 1000 == 0:
            logger.debug("Mouse VAE Loss: %.6f, %d epochs" % (loss[0], epoch))
    mouseVAE.encoder.model.save("models/mouse_e.h5")
    mouseVAE.decoder.model.save("models/mouse_d.h5")
    mcai.clearSession()
    logger.debug("End: Mouse VAE Learning")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status = 500
        if ".h5" in self.path:
            if MODEL_WRITING:
                response = {
                    'status': 'ng',
                    'message': 'Writing model...'
                }
                status = 503
            else:
                fileName = self.path[1:]
                if os.path.exists("models/%s" % fileName):
                    self.send_response(200)
                    self.send_header('Content-type', 'application/octet-stream')
                    self.end_headers()
                    with open("models/%s" % fileName, "rb") as f:
                        self.wfile.write(f.read())
                    return
                else:
                    response = {
                        'status': 'ng',
                        'message': 'File not found'
                    }
                    status = 404
        elif self.path == "/hello":
            response = {
                "status": "ok",
                "info": {
                    "type": "learn"
                }
            }
            status = 200
        else:
            currentVersion = {
                "version": 0,
                "count": 0
            }
            if os.path.exists('models/version.json'):
                with open("models/version.json", "r") as f:
                    currentVersion = json.load(f)
            response = {
                'status': 'ok',
                'version': currentVersion["version"],
                'count': currentVersion["count"]
            }
            status = 200
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        responseBody = json.dumps(response)
        self.wfile.write(responseBody.encode('utf-8'))


    def do_POST(self):
        try:
            content_len=int(self.headers.get('content-length'))
            id = str(self.headers.get('id'))
            if self.path == "/video":
                with open(os.path.join(SAVE_FOLDER, "%s.mp4" % (id)), "wb") as f:
                    f.write(self.rfile.read(content_len))
                status_code = 200
                response = {
                    'status': 'ok'
                }
            else:
                requestBody = json.loads(self.rfile.read(content_len).decode('utf-8'))
                if "data" in requestBody:
                    if len(requestBody["data"]) > 0:
                        with open(os.path.join(SAVE_FOLDER, "%s.json" % (id)), "w") as f:
                            json.dump(requestBody, f, indent=4)
                status_code = 200
                response = {
                    'status' : "ok",
                }
            self.send_response(status_code)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            responseBody = json.dumps(response)

            self.wfile.write(responseBody.encode('utf-8'))
            threading.Thread(target=check).start()
        except Exception as e:
            print("An error occured")
            print("The information of error is as following")
            print(type(e))
            print(e.args)
            print(e)
            response = {
                'status' : 500,
                'msg' : 'An error occured'
            }

            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            responseBody = json.dumps(response)

            self.wfile.write(responseBody.encode('utf-8'))

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

if __name__ == '__main__':
    threading.Thread(target=check).start()
    server = ThreadedHTTPServer(("0.0.0.0", 8000), Handler)
    server.serve_forever()
