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

videoFrames, moveFrames, learnFramesBuffer = {}, {}, []

if not os.path.exists("models/"):
    os.mkdir("models")

# Search for Central Server
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

# Image Size
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
critic.model.compile(loss="mse", optimizer="Adam")
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
    rewardEst = np.empty((learnDataLength, 1))
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
        rewardEst[i] = learn_data[i][15].reshape((1))
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
    return input_data, output_data, rewardEst

def convFrame(ld, reward):
    inpdata = []
    inpdata.append(np.array([convBit(ld["input"]["mem"]["reg"])]))
    inpdata.append(np.array([ld["input"]["mem"]["data"]]))
    inpdata.append(np.array([convBit(ld["input"]["mem"]["reg2"])]))
    inpdata.append(np.array([ld["input"]["mem"]["data2"]]))
    inpdata.append(np.array([convName(ld["input"]["chat"]["name"])]))
    inpdata.append(np.array([convChar(ld["input"]["chat"]["message"])]))
    inpdata.append(np.array([ld["output"]["keyboard"]]))
    inpdata.append(np.array([ld["output"]["mouse"]["dir"]]))
    inpdata.append(np.array([ld["output"]["mouse"]["button"]]))
    inpdata.append(np.array([convBit(ld["output"]["mem"]["save"])]))
    inpdata.append(np.array([ld["output"]["mem"]["mem"]]))
    inpdata.append(np.array([convBit(ld["output"]["mem"]["reg"])]))
    inpdata.append(np.array([convBit(ld["output"]["mem"]["reg2"])]))
    inpdata.append(np.array([convChar(ld["output"]["chat"])]))
    inpdata.append(np.array([reward]))
    return inpdata

def convChar(char):
    data = np.zeros((CHARS_COUNT))
    for i in range(CHARS_COUNT):
        if chars["chars"][i] == char:
            data[i] = 1
    return data

def bin2Char(bin):
    return chars["chars"][np.argmax(bin)]

def bin2Name(bin):
    name = ""
    for b in bin:
        char = bin2Char(b)
        if char != "\n":
            name += char
        else:
            break
    return name

def convName(name):
    remain = 6 - len(name)
    data = [convChar(name[i]) for i in range(len(name))]
    for i in range(remain):
        data.append(convChar("\n"))
    return data

def getBit(value, bit):
    return value >> bit & 0b1

def convBit(value):
    return np.array([getBit(value, i) for i in range(7, -1, -1)])

CHECK_PROCESSING = False
MODEL_WRITING = False
CHECK_FIRSTRUN = True

def checkCount():
    global learnFramesBuffer
    return len(learnFramesBuffer)

def check():
    global data, videoFrames, moveFrames, learnFramesBuffer
    global CHECK_PROCESSING, CHECK_FIRSTRUN, LEARN_LIMIT, TRAINING
    listIDs = list(videoFrames.keys())
    listIDs.extend(list(moveFrames.keys()))
    ids = [id for id in set(listIDs) if listIDs.count(id) == 2]
    learnFrameCount = len(learnFramesBuffer)

    if len(ids) >= 10 and not CHECK_PROCESSING and not TRAINING:
        CHECK_PROCESSING = True
        counts = []
        idsCopy = ids.copy()
        for i in range(len(ids)):
            id = ids[i]
            count = len(moveFrames[id]["data"])
            if count >= 2:
                counts.append(count)
                continue
            videoFrames.pop(id)
            moveFrames.pop(id)
            idsCopy.remove(id)
        ids = idsCopy.copy()
        if len(counts) > 0:
            for id in ids:
                data = moveFrames[id]
                healthData = [min(data["data"][i]["health"] * (1 if not (i + 1) % 20 == 0 else 1.25 if not (i + 1) % 100 == 0 else 15), 20) for i in range(len(data["data"]))]
                rewardEst = np.array([sum(healthData[dp:])/(len(healthData)-dp) for dp in range(len(healthData))]).reshape(len(healthData), 1) / 20
                for i in range(len(data["data"])):
                    daf = convFrame(data["data"][i], rewardEst[i])
                    img = videoFrames[id][i]
                    learnFramesBuffer.append({"data": daf, "img": img})
                    if len(learnFramesBuffer) > LEARN_LIMIT:
                        learnFramesBuffer.pop(0)
                moveFrames.pop(id)
                videoFrames.pop(id)
        learnFrameCount = checkCount()
        CHECK_FIRSTRUN = False
        logger.debug("Check done, current total frames: %d/%d" % (learnFrameCount, LEARN_LIMIT))
        CHECK_PROCESSING = False

    # First Run
    if CHECK_FIRSTRUN:
        learnFrameCount = checkCount()
        logger.debug("First Run, current total frames: %d" % (learnFrameCount))
        CHECK_FIRSTRUN = False
        TRAINING = True
        if not os.path.exists("models/char_e.h5") or not os.path.exists("models/char_d.h5"):
            charVAELearn()
        if not os.path.exists("models/keyboard_e.h5") or not os.path.exists("models/keyboard_d.h5"):
            keyboardVAELearn()
        if not os.path.exists("models/mouse_e.h5") or not os.path.exists("models/mouse_d.h5"):
            mouseVAELearn()
        if os.path.exists("models/model.h5") and os.path.exists("models/critic.h5"):
            actor.model.load_weights("models/model.h5")
            critic.model.load_weights("models/critic.h5")
        if os.path.exists("models/vae_e.h5"):
            actor.encoder.model.load_weights("models/vae_e.h5")
            critic.encoder.model.load_weights("models/vae_e.h5")
        actor.charencoder.model.load_weights("models/char_e.h5")
        for c in actor.nameencoder.chars:
            c.model.load_weights("models/char_e.h5")
        actor.keyboarddecoder.model.load_weights("models/keyboard_d.h5")
        actor.mousedecoder.model.load_weights("models/mouse_d.h5")
        critic.charencoder.model.load_weights("models/char_e.h5")
        for c in critic.nameencoder.chars:
            c.model.load_weights("models/char_e.h5")
        critic.keyboardencoder.model.load_weights("models/keyboard_e.h5")
        critic.mouseencoder.model.load_weights("models/mouse_e.h5")
        critic.actorcharencoder.model.load_weights("models/char_e.h5")
        TRAINING = False
    if learnFrameCount >= (LEARN_LIMIT * 0.75) and not TRAINING:
        learn()

def learn():
    global LEARN_LIMIT, TRAINING, MODEL_WRITING
    global model, vae, learnFramesBuffer
    batchSize = 32
    if TRAINING: return
    TRAINING = True
    logger.info("Start Learning")

    learnFrames = random.sample(learnFramesBuffer, LEARN_LIMIT // 2)
    iters = len(learnFrames) // batchSize

    '''
    # Image VAE Learning
    if os.path.exists("models/vae_d_latest.h5") and os.path.exists("models/vae_e_latest.h5"):
        vae.decoder.model.load_weights("models/vae_d_latest.h5")
        vae.encoder.model.load_weights("models/vae_e_latest.h5")
    vaeFrames = np.empty((LEARN_LIMIT // 2, 256, 256, 3), dtype=np.uint8)
    for i in range(len(learnFrames)):
        vaeFrames[i] = learnFrames[i]["img"]
    logger.debug("Start: Image VAE Learning")
    for epoch in range(1):
        for iter in range(iters):
            loss = vae.model.train_on_batch(vaeFrames[iter*batchSize:(iter+1)*batchSize]/255, vaeFrames[iter*batchSize:(iter+1)*batchSize]/255)
            if iter % 10 == 0:
                logger.debug("Image VAE Loss: %.6f, %d epochs, %d iters" % (loss, epoch, iter))
    del vaeFrames
    vae.encoder.model.save("models/vae_e_latest.h5")
    vae.decoder.model.save("models/vae_d_latest.h5")

    vaeOverride = random.random() < 0
    if not os.path.exists("models/vae_e.h5") or not os.path.exists("models/vae_d.h5") or vaeOverride:
        logger.debug("Image VAE Model Updated")
        shutil.copy("models/vae_e_latest.h5", "models/vae_e.h5")
        shutil.copy("models/vae_d_latest.h5", "models/vae_d.h5")
        actor.encoder.model.load_weights("models/vae_e.h5")
        critic.encoder.model.load_weights("models/vae_e.h5")
    mcai.clearSession()
    logger.debug("End: Image VAE Learning")
    '''

    thisEpochs = EPOCHS

    # Critic Learning
    for epoch in range(thisEpochs):
        loss_history = []
        for iter in range(iters):
            batchFrames = learnFrames[iter*batchSize:(iter+1)*batchSize]
            for frame in batchFrames:
                frameData = []
                frameImg = frame["img"].reshape(1, 256, 256, 3) / 255
                frameData.append(frameImg)
                frameData.extend(frame["data"])
                learn_data.append(frameData)
            x, y, rewardEst = convAll()
            x = x[:-1]
            x.extend(y)
            y = rewardEst
            loss = critic.model.train_on_batch(x, y)
            loss_history.append(loss)
        logger.info("Critic Loss: %.6f, %d epochs" % (sum(loss_history)/len(loss_history), epoch))

    # Actor Learning
    for epoch in range(thisEpochs):
        loss_history = []
        for iter in range(iters):
            batchFrames = learnFrames[iter*batchSize:(iter+1)*batchSize]
            for frame in batchFrames:
                frameData = []
                frameImg = frame["img"].reshape(1, 256, 256, 3) / 255
                frameData.append(frameImg)
                frameData.extend(frame["data"])
                learn_data.append(frameData)
            x, _, rewardEst = convAll()
            realEst = combined.predict(x, verbose=0)
            y = np.maximum(rewardEst, realEst)
            print(np.all(y == rewardEst), np.all(y == realEst))
            loss = combined.train_on_batch(x, y)
            loss_history.append(loss)
        logger.info("Actor Loss: %.6f, %d epochs" % (sum(loss_history)/len(loss_history), epoch))

    MODEL_WRITING = True
    actor.model.save("models/model.h5")
    critic.model.save("models/critic.h5")
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
    logger.info("Finish Learning")

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
            if self.path == "/videoND":
                width = int(self.headers.get('width'))
                height = int(self.headers.get('height'))
                frameCount = int(self.headers.get('frameCount'))
                videoFrames[id] = np.frombuffer(self.rfile.read(content_len), dtype=np.uint8).reshape((frameCount, height, width, 3))
                status_code = 200
                response = {
                    'status': 'ok'
                }
            else:
                requestBody = json.loads(self.rfile.read(content_len).decode('utf-8'))
                if "data" in requestBody:
                    if len(requestBody["data"]) > 0:
                        moveFrames[id] = requestBody
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
