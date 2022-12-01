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

logger = getLogger(__name__)
logger.setLevel(DEBUG)
logger_handler = StreamHandler()
logger_formatter = Formatter(fmt='%(asctime)-15s [%(name)s] %(message)s')
logger_handler.setFormatter(logger_formatter)
logger.addHandler(logger_handler)

SERV_TYPE = "learn"

CHECK_FIRSTRUN = True

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
VIDEO_FOLDER = config["video_folder"]
if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)
if not os.path.exists(VIDEO_FOLDER):
    os.makedirs(VIDEO_FOLDER)

WIDTH = config["resolution"]["x"]
HEIGHT = config["resolution"]["y"]

EPOCHS = config["epochs"]

with open(config["char_file"], "r") as f:
    chars = json.loads(f.read())

CHARS_COUNT = len(chars["chars"])

data = []
learn_data = []
training = False
vae = mcai.image.ImageVAE()
model = mcai.mcAI(WIDTH=WIDTH, HEIGHT=HEIGHT, CHARS_COUNT=CHARS_COUNT, logger=logger)

def limit(i):
    i[i>1]=1
    i[i<0]=0
    return i

def nichi(i):
    i[i>=0.5]=1
    i[i<0.5]=0
    return i

def convertData():
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

def conv_data(ld):
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

def check():
    global training
    global learn_data
    global data
    global CHECK_PROCESSING
    global CHECK_FIRSTRUN
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
                shutil.copy(os.path.join(DATA_FOLDER, "%s.mp4" % (id)), os.path.join(VIDEO_FOLDER, "%s.mp4" % (id)))
                shutil.move(os.path.join(SAVE_FOLDER, "%s.json" % (id)), os.path.join(DATA_FOLDER, "%s.json" % (id)))
                with open(os.path.join(DATA_FOLDER, "%s.json" % (id)), "r") as f:
                    data = json.loads(f.read())
                c_data = []
                for d in data["data"]:
                    daf = conv_data(d)
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
    if sum(learn_counts) >= 1000 and not training:
        training = True
        #if os.path.exists("model.h5"):
        #    model.model.load_weights("model.h5")
        logger.info("Start Learning")
        logger.debug("Start: VAE Learning [Alpha]")
        vae = mcai.image.ImageVAE()
        video_ids = [file.replace(".mp4", "") for file in os.listdir(VIDEO_FOLDER) if ".mp4" in file.lower() and file[0] != "."]
        for epoch in range(EPOCHS):
            i = 0
            video = cv2.VideoCapture(os.path.join(VIDEO_FOLDER, "%s.mp4" % (video_ids[i])))
            frames = np.empty((0, 256, 256, 3), dtype=np.uint8)
            while True:
                ret, frame = video.read()
                if not ret:
                    video.release()
                    if i < len(video_ids) - 1:
                        i += 1
                        video = cv2.VideoCapture(os.path.join(VIDEO_FOLDER, "%s.mp4" % (video_ids[i])))
                        continue
                    else:
                        vae.model.train_on_batch(frames/255, frames/255)
                        break
                try:
                    frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((256,256))
                    frames = np.append(frames, np.array(frame).astype("uint8").reshape((1,256,256,3)), axis=0)
                except:
                    logger.warning("Frame Skipped")
                    logger.warning(frame)
                if frames.shape[0] >= 10:
                    loss = vae.model.train_on_batch(frames/255, frames/255)
                    logger.debug("VAE Loss: %.6f" % (loss))
                    frames = np.empty((0, 256, 256, 3), dtype=np.uint8)
        vae.encoder.model.save("encoder.h5")
        logger.debug("End: VAE Learning [Alpha]")
        total_count = 0
        now_count = 0
        mx, mn = max(learn_counts), min(learn_counts)
        ave, pow_ave = sum(learn_counts) / len(learn_counts), sum([count ** 2 for count in learn_counts]) / len(learn_counts)
        max_dis = mx - ave
        for count in learn_counts:
            a, b = int(count / 10), count % 10
            if b > 0:
                a += 1
            total_count += a
        total_count *= EPOCHS
        model = mcai.mcAI(WIDTH=WIDTH, HEIGHT=HEIGHT, CHARS_COUNT=CHARS_COUNT, logger=logger)
        model.encoder.model.load_weights("encoder.h5")
        for epoch in range(EPOCHS):
            for id in learn_ids:
                with open(os.path.join(DATA_FOLDER, "%s.pkl" % (id)), "rb") as f:
                    l_data = pickle.load(f)
                count = len(l_data)
                point = (count - ave) / max_dis
                a, b = int(count / 10), count % 10
                video = cv2.VideoCapture(os.path.join(DATA_FOLDER, "%s.mp4" % (id)))
                all_count = a
                if b > 0:
                    all_count += 1
                video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                for i in range(all_count):
                    c = b
                    if i != a:
                        c = 10
                    learn_data = []
                    for x in range(c):
                        f = []
                        try:
                            _, frame = video.read()
                            frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((WIDTH, HEIGHT))
                        except:
                            break
                        f.append(np.array(frame).reshape((1, HEIGHT, WIDTH, 3)))
                        f_ctrls = l_data[i*10+x]
                        for v in range(8):
                            f_ctrls[6+v] = f_ctrls[6+v] * point
                            if point < 0:
                                f_ctrls[6+v] = f_ctrls[6+v] + 1
                        for f_ctrl in f_ctrls:
                            f.append(f_ctrl)
                        learn_data.append(f)
                    x, y = convertData()
                    try:
                        model.model.train_on_batch(x, y)
                    except:
                        logger.error("Training failure, skipped...")
                    now_count += 1
                    if now_count % 10 == 0:
                        logger.debug("Learning Progress: %d/%d (%.1f%%)" % (now_count, total_count, now_count/total_count*100))
                if epoch >= EPOCHS-1:
                    os.remove(os.path.join(DATA_FOLDER, "%s.mp4" % (id)))
                    os.remove(os.path.join(DATA_FOLDER, "%s.pkl" % (id)))
        logger.info("Finish Learning")
        model.model.save("model.h5")
        with open("version", "w") as f:
            f.write(str(int(datetime.now().timestamp())))
        training = False

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not self.path == "/model.h5":
            version = 0
            if os.path.exists('version'):
                with open("version", "r") as f:
                    version = int(f.read())
            response = {
                'status': 'ok',
                'version': version
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            responseBody = json.dumps(response)
            self.wfile.write(responseBody.encode('utf-8'))
        elif self.path == "/hello":
            response = {
                "status": "ok",
                "info": {
                    "type": "learn"
                }
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            responseBody = json.dumps(response)
            self.wfile.write(responseBody.encode('utf-8'))
        else:
            if training:
                response = {
                    'status': 'ng', 
                    'error': 'training'
                }
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                responseBody = json.dumps(response)
                self.wfile.write(responseBody.encode('utf-8'))
            else:
                if os.path.exists("model.h5"):
                    self.send_response(200)
                    self.send_header('Content-type', 'application/octet-stream')
                    self.end_headers()
                    self.wfile.write(open("model.h5", "rb").read())
                else:
                    response = {
                        'status': 'ng', 
                        'msg': 'not found'
                    }
                    self.send_response(404)
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