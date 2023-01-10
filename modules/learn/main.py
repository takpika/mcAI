from http.server import HTTPServer, BaseHTTPRequestHandler
import shutil
from socketserver import ThreadingMixIn
import threading
import json, mcai, argparse, os, psutil, socket, requests, subprocess, random, pickle, cv2
from time import sleep
import numpy as np
from datetime import datetime
from logging import getLogger, DEBUG, StreamHandler, Formatter
from PIL import Image
import tensorflow as tf

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
    sleep(0.1)

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

data = []
learn_data = []
training = False
vae = mcai.image.ImageVAE()
charVAE = mcai.text.CharVAE(CHARS_COUNT)
keyboardVAE = mcai.control.KeyboardVAE()
mouseVAE = mcai.control.MouseVAE()
model = mcai.mcAI(WIDTH=WIDTH, HEIGHT=HEIGHT, CHARS_COUNT=CHARS_COUNT, logger=logger)

def limit(i):
    i[i>1]=1
    i[i<0]=0
    return i

def nichi(i):
    i[i>=0.5]=1
    i[i<0.5]=0
    return i

def conv_all():
    x_img = np.empty((0, HEIGHT, WIDTH, 3))
    x_reg = np.empty((0, 8))
    x_mem = np.empty((0, 8))
    x_reg2 = np.empty((0, 8))
    x_mem2 = np.empty((0, 8))
    x_name = np.empty((0, 6, CHARS_COUNT))
    x_mes = np.empty((0, CHARS_COUNT))
    ai_k = np.empty((0, 17))
    ai_m_1 = np.empty((0, 2))
    ai_m_2 = np.empty((0, 2))
    ai_mem_1 = np.empty((0, 8))
    ai_mem_2 = np.empty((0, 8))
    ai_mem_3 = np.empty((0, 8))
    ai_mem_4 = np.empty((0, 8))
    ai_chat = np.empty((0, CHARS_COUNT))
    global learn_data
    for ld in learn_data:
        x_img = np.append(x_img, ld[0].reshape((1,HEIGHT,WIDTH,3)), axis=0)
        x_reg = np.append(x_reg, ld[1].reshape((1,8)), axis=0)
        x_mem = np.append(x_mem, ld[2].reshape((1,8)), axis=0)
        x_reg2 = np.append(x_reg2, ld[3].reshape((1,8)), axis=0)
        x_mem2 = np.append(x_mem2, ld[4].reshape((1,8)), axis=0)
        x_name = np.append(x_name, ld[5].reshape((1,6,CHARS_COUNT)), axis=0)
        x_mes = np.append(x_mes, ld[6].reshape((1,CHARS_COUNT)), axis=0)
        ai_k = np.append(ai_k, ld[7].reshape((1,17)), axis=0)
        ai_m_1 = np.append(ai_m_1, ld[8].reshape((1,2)), axis=0)
        ai_m_2 = np.append(ai_m_2, ld[9].reshape((1,2)), axis=0)
        ai_mem_1 = np.append(ai_mem_1, ld[10].reshape((1,8)), axis=0)
        ai_mem_2 = np.append(ai_mem_2, ld[11].reshape((1,8)), axis=0)
        ai_mem_3 = np.append(ai_mem_3, ld[12].reshape((1,8)), axis=0)
        ai_mem_4 = np.append(ai_mem_4, ld[13].reshape((1,8)), axis=0)
        ai_chat = np.append(ai_chat, ld[14].reshape((1,CHARS_COUNT)), axis=0)
    if random.random() < 0.1:
        ai_k += (np.random.random(ai_k.shape)-0.5)
    if random.random() < 0.1:
        ai_m_1 += (np.random.random(ai_m_1.shape)-0.5)
    if random.random() < 0.1:
        ai_m_2 += (np.random.random(ai_m_2.shape)-0.5)
    ai_k = limit(ai_k)
    ai_m_1 = limit(ai_m_1)
    ai_m_2 = limit(ai_m_2)
    ai_mem_1 = nichi(ai_mem_1)
    ai_mem_2 = nichi(ai_mem_2)
    ai_mem_3 = nichi(ai_mem_3)
    ai_mem_4 = nichi(ai_mem_4)
    ai_chat = limit(ai_chat)
    input_data = model.make_input(
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

def check():
    global training, learn_data, data
    global CHECK_PROCESSING, CHECK_FIRSTRUN, MODEL_WRITING, LEARN_LIMIT
    global model, vae
    list_ids = [file.replace(".mp4","").replace(".json","") for file in os.listdir(SAVE_FOLDER)]
    ids = [id for id in set(list_ids) if list_ids.count(id) == 2]
    learn_counts = [0]
    if len(ids) >= 10 and not CHECK_PROCESSING:
        CHECK_PROCESSING = True
        counts = [len(json.loads(open(os.path.join(SAVE_FOLDER, "%s.json" % (id)), "r").read())["data"]) for id in ids if len(json.loads(open(os.path.join(SAVE_FOLDER, "%s.json" % (id)), "r").read())["data"]) >= 2]
        if len(counts) > 0:
            for id in ids:
                shutil.move(os.path.join(SAVE_FOLDER, "%s.mp4" % (id)), os.path.join(DATA_FOLDER, "%s.mp4" % (id)))
                shutil.move(os.path.join(SAVE_FOLDER, "%s.json" % (id)), os.path.join(DATA_FOLDER, "%s.json" % (id)))
                with open(os.path.join(DATA_FOLDER, "%s.json" % (id)), "r") as f:
                    data = json.loads(f.read())
                c_data = []
                for d in data["data"]:
                    daf = conv_frame(d)
                    c_data.append(daf)
                with open(os.path.join(DATA_FOLDER, "%s.pkl" % (id)), "wb") as f:
                    pickle.dump(c_data, f)
                os.remove(os.path.join(DATA_FOLDER, "%s.json" % (id)))
        learn_list_ids = [file.replace(".mp4","").replace(".pkl","") for file in os.listdir(DATA_FOLDER)]
        learn_ids = [id for id in set(learn_list_ids) if learn_list_ids.count(id) == 2]
        learn_counts = [len(pickle.load(open(os.path.join(DATA_FOLDER, "%s.pkl" % (id)), "rb"))) for id in learn_ids]
        CHECK_FIRSTRUN = False
        logger.debug("Check done, current total frames: %d" % (sum(learn_counts)))
        CHECK_PROCESSING = False
    if CHECK_FIRSTRUN:
        learn_list_ids = [file.replace(".mp4","").replace(".pkl","") for file in os.listdir(DATA_FOLDER)]
        learn_ids = [id for id in set(learn_list_ids) if learn_list_ids.count(id) == 2]
        learn_counts = [len(pickle.load(open(os.path.join(DATA_FOLDER, "%s.pkl" % (id)), "rb"))) for id in learn_ids]
        logger.debug("First Run, current total frames: %d" % (sum(learn_counts)))
        CHECK_FIRSTRUN = False
        training = True
        if not os.path.exists("models/char_e.h5") or not os.path.exists("models/char_d.h5"):
            logger.debug("Start: Char VAE Learning")
            for epoch in range(100000):
                x = np.random.random((100, CHARS_COUNT))
                x = np.where(x == x.max(axis=1, keepdims=True), 1, 0)
                loss = charVAE.model.train_on_batch(x, x)
                if epoch % 1000 == 0:
                    logger.debug("Char VAE Loss: %.6f, %d epochs" % (loss, epoch))
            charVAE.encoder.model.save("models/char_e.h5")
            charVAE.decoder.model.save("models/char_d.h5")
            model.clearSession()
            logger.debug("End: Char VAE Learning")
        if not os.path.exists("models/keyboard_e.h5") or not os.path.exists("models/keyboard_d.h5"):
            logger.debug("Start: Keyboard VAE Learning")
            for epoch in range(100000):
                x = np.random.random((100, 17))
                x = np.where(x >= 0.5, 1, 0)
                loss = keyboardVAE.model.train_on_batch(x, x)
                if epoch % 1000 == 0:
                    logger.debug("Keyboard VAE Loss: %.6f, %d epochs" % (loss, epoch))
            keyboardVAE.encoder.model.save("models/keyboard_e.h5")
            keyboardVAE.decoder.model.save("models/keyboard_d.h5")
            model.clearSession()
            logger.debug("End: Keyboard VAE Learning")
        if not os.path.exists("models/mouse_e.h5") or not os.path.exists("models/mouse_d.h5"):
            logger.debug("Start: Mouse VAE Learning")
            for epoch in range(100000):
                x_dir = np.random.random((100, 2))
                x_btn = np.random.random((100, 2))
                x_btn = np.where(x_btn >= 0.5, 1, 0)
                loss = mouseVAE.model.train_on_batch([x_dir, x_btn], [x_dir, x_btn])
                if epoch % 1000 == 0:
                    logger.debug("Mouse VAE Loss: %.6f, %d epochs" % (loss[0], epoch))
            mouseVAE.encoder.model.save("models/mouse_e.h5")
            mouseVAE.decoder.model.save("models/mouse_d.h5")
            model.clearSession()
            logger.debug("End: Mouse VAE Learning")
        training = False
    if sum(learn_counts) >= LEARN_LIMIT and not training:
        training = True
        logger.info("Start Learning")
        logger.debug("Start: Image VAE Learning")
        if os.path.exists("models/vae_d.h5") and os.path.exists("models/vae_e.h5"):
            vae.decoder.model.load_weights("models/vae_d.h5")
            vae.encoder.model.load_weights("models/vae_e.h5")
        video_ids = [file.replace(".mp4", "") for file in os.listdir(DATA_FOLDER) if ".mp4" in file.lower() and file[0] != "."]
        for epoch in range(2):
            i = 0
            count = 0
            video = cv2.VideoCapture(os.path.join(DATA_FOLDER, "%s.mp4" % (video_ids[i])))
            frames = np.empty((0, 256, 256, 3), dtype=np.uint8)
            while True:
                ret, frame = video.read()
                if not ret:
                    video.release()
                    if i < len(video_ids) - 1:
                        i += 1
                        video = cv2.VideoCapture(os.path.join(DATA_FOLDER, "%s.mp4" % (video_ids[i])))
                        continue
                    else:
                        vae.model.train_on_batch(frames/255, frames/255)
                        frames = np.empty((0, 256, 256, 3), dtype=np.uint8)
                        break
                try:
                    frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((256,256))
                    frames = np.append(frames, np.array(frame).astype("uint8").reshape((1,256,256,3)), axis=0)
                except:
                    logger.warning("Frame Skipped")
                    logger.warning(frame)
                if frames.shape[0] >= 30:
                    count += 1
                    loss = vae.model.train_on_batch(frames/255, frames/255)
                    if count % 10 == 0:
                        logger.debug("Image VAE Loss: %.6f, %d epochs, %3d" % (loss, epoch, count))
                    frames = np.empty((0, 256, 256, 3), dtype=np.uint8)
        vae.encoder.model.save("models/vae_e.h5")
        vae.decoder.model.save("models/vae_d.h5")
        model.clearSession()
        logger.debug("End: Image VAE Learning")
        total_count = 0
        now_count = 0
        mx = max(learn_counts)
        ave = sum(learn_counts) / len(learn_counts)
        LEARN_THRESHOLD = mx * 0.9
        if ave + (mx - ave) * 0.5 > LEARN_THRESHOLD:
            LEARN_THRESHOLD = ave + (mx - ave) * 0.5
        if mx * 10 > LEARN_LIMIT:
            LEARN_LIMIT = mx * 10
            if LEARN_LIMIT % 100 != 0:
                LEARN_LIMIT += 100 - LEARN_LIMIT % 100
            logger.debug("Learn Limit has Changed: %d" % (LEARN_LIMIT))
        for count in learn_counts:
            if count < LEARN_THRESHOLD:
                continue
            a, b = int(count / 30), count % 30
            if b > 0:
                a += 1
            total_count += a
        total_count *= EPOCHS
        model.encoder.model.load_weights("models/vae_e.h5")
        model.charencoder.model.load_weights("models/char_e.h5")
        for c in model.nameencoder.chars:
            c.model.load_weights("models/char_e.h5")
        model.keyboarddecoder.model.load_weights("models/keyboard_d.h5")
        model.mousedecoder.model.load_weights("models/mouse_d.h5")
        learn_data.clear()
        for epoch in range(EPOCHS):
            for id in learn_ids:
                with open(os.path.join(DATA_FOLDER, "%s.pkl" % (id)), "rb") as f:
                    l_data = pickle.load(f)
                count = len(l_data)
                if count < LEARN_THRESHOLD:
                    if epoch == EPOCHS - 1:
                        os.remove(os.path.join(DATA_FOLDER, "%s.mp4" % (id)))
                        os.remove(os.path.join(DATA_FOLDER, "%s.pkl" % (id)))
                    continue
                point = count / mx
                a, b = int(count / 30), count % 30
                video = cv2.VideoCapture(os.path.join(DATA_FOLDER, "%s.mp4" % (id)))
                all_count = a
                if b > 0:
                    all_count += 1
                video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                for i in range(all_count):
                    c = b
                    if i != a:
                        c = 30
                    learn_data = []
                    for x in range(c):
                        f = []
                        try:
                            _, frame = video.read()
                            frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((WIDTH, HEIGHT))
                        except:
                            break
                        f.append(np.array(frame).reshape((1, HEIGHT, WIDTH, 3)) / 255)
                        f_ctrls = l_data[i*30+x]
                        for v in range(8):
                            f_ctrls[6+v] = (f_ctrls[6+v] - 0.5) * point + 0.5
                            f_ctrls[6+v] = np.where(f_ctrls[6+v] < 0.5, 0, 1)
                        for f_ctrl in f_ctrls:
                            f.append(f_ctrl)
                        learn_data.append(f)
                    x, y = conv_all()
                    loss = -1
                    try:
                        loss = model.model.train_on_batch(x, y)
                    except:
                        logger.error("Training failure, skipped...")
                    now_count += 1
                    if now_count % 10 == 0:
                        logger.debug("Learning Progress: %d/%d (%.1f%%) loss: %.6f" % (now_count, total_count, now_count/total_count*100, loss[0]))
                video.release()
        logger.info("Finish Learning")
        MODEL_WRITING = True
        model.model.save("models/model.h5")
        MODEL_WRITING = False
        model.clearSession()
        with open("models/version", "w") as f:
            f.write(str(int(datetime.now().timestamp())))
        training = False

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
            version = 0
            if os.path.exists('models/version'):
                with open("models/version", "r") as f:
                    version = int(f.read())
            response = {
                'status': 'ok',
                'version': version
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
                #    if len(requestBody["data"]) > 0:
                #        data.append(requestBody)
                #        threading.Thread(target=check).start()
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