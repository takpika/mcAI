import json, os, time, random, gc
import numpy as np
from LearnHandler import LearnHandler

from mcai.ai import Actor, Critic
from mcai.module import ModuleCore

from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input
import tensorflow as tf

class Learn(ModuleCore):
    def __init__(self):
        super().__init__()
        if not os.path.exists("models/"):
            os.mkdir("models")
        self.getLogger()
        if __name__ == "__main__":
            self.logger.info("Searching for Central Server...")
            self.searchCentral()
            if self.CENTRAL_IP == None:
                self.logger.error("Central Server not found")
                exit(1)
            self.logger.info("Central Server IP: " + self.CENTRAL_IP)
            self.getConfig()
            self.setConfig()
            self.buildModel()

    def setConfig(self):
        self.GPU_AVAIL = tf.test.is_gpu_available()
        self.videoFrames = {}
        self.moveFrames = {}
        self.learnFramesBuffer = []
        self.learn_data = []
        self.CENTRAL_IP = None
        self.WIDTH = self.config["resolution"]["x"]
        self.HEIGHT = self.config["resolution"]["y"]
        self.LEARN_LIMIT = 4096
        self.USE_LEARN_LIMIT = 3
        self.TRAINING = False
        self.CHECK_PROCESSING = False
        self.MODEL_WRITING = False
        self.CHECK_FIRSTRUN = True
        self.EPOCHS = self.config["epochs"]
        with open(self.config["char_file"], "r") as f:
            self.chars = json.loads(f.read())
        self.CHARS_COUNT = len(self.chars["chars"])

    def convAll(self):
        learnDataLength = len(self.learn_data)
        x_img = np.empty((learnDataLength, self.HEIGHT, self.WIDTH, 3))
        x_reg = np.empty((learnDataLength, 8))
        x_mem = np.empty((learnDataLength, 8))
        x_reg2 = np.empty((learnDataLength, 8))
        x_mem2 = np.empty((learnDataLength, 8))
        x_name = np.empty((learnDataLength, 6, self.CHARS_COUNT))
        x_mes = np.empty((learnDataLength, self.CHARS_COUNT))
        ai_k = np.empty((learnDataLength, 17))
        ai_m_1 = np.empty((learnDataLength, 2))
        ai_m_2 = np.empty((learnDataLength, 2))
        ai_mem_1 = np.empty((learnDataLength, 8))
        ai_mem_2 = np.empty((learnDataLength, 8))
        ai_mem_3 = np.empty((learnDataLength, 8))
        ai_mem_4 = np.empty((learnDataLength, 8))
        ai_chat = np.empty((learnDataLength, self.CHARS_COUNT))
        rewardEst = np.empty((learnDataLength, 1))
        for i in range(learnDataLength):
            x_img[i] = self.learn_data[i][0].reshape((self.HEIGHT,self.WIDTH,3))
            x_reg[i] = self.learn_data[i][1].reshape((8))
            x_mem[i] = self.learn_data[i][2].reshape((8))
            x_reg2[i] = self.learn_data[i][3].reshape((8))
            x_mem2[i] = self.learn_data[i][4].reshape((8))
            x_name[i] = self.learn_data[i][5].reshape((6, self.CHARS_COUNT))
            x_mes[i] = self.learn_data[i][6].reshape((self.CHARS_COUNT))
            ai_k[i] = self.learn_data[i][7].reshape((17))
            ai_m_1[i] = self.learn_data[i][8].reshape((2))
            ai_m_2[i] = self.learn_data[i][9].reshape((2))
            ai_mem_1[i] = self.learn_data[i][10].reshape((8))
            ai_mem_2[i] = self.learn_data[i][11].reshape((8))
            ai_mem_3[i] = self.learn_data[i][12].reshape((8))
            ai_mem_4[i] = self.learn_data[i][13].reshape((8))
            ai_chat[i] = self.learn_data[i][14].reshape((self.CHARS_COUNT))
            rewardEst[i] = self.learn_data[i][15].reshape((1))
        ai_k = np.clip(ai_k, 0, 1)
        ai_m_1 = np.clip(ai_m_1, -1, 1)
        ai_m_2 = np.clip(ai_m_2, 0, 1)
        ai_mem_1 = np.where(ai_mem_1<0.5, 0, 1)
        ai_mem_2 = np.where(ai_mem_2<0.5, 0, 1)
        ai_mem_3 = np.where(ai_mem_3<0.5, 0, 1)
        ai_mem_4 = np.where(ai_mem_4<0.5, 0, 1)
        ai_chat = np.clip(ai_chat, 0, 1)
        input_data = Actor(WIDTH=self.WIDTH, HEIGHT=self.HEIGHT, CHARS_COUNT=self.CHARS_COUNT).make_input(
            x_img, x_reg, x_mem, x_reg2, x_mem2, np.transpose(x_name, (1,0,2)), x_mes, x_img.shape[0]
        )
        output_data = [
            ai_k, [ai_m_1, ai_m_2], [ai_mem_1, ai_mem_2, ai_mem_3, ai_mem_4], ai_chat
        ]
        self.learn_data.clear()
        return input_data, output_data, rewardEst
    
    def buildModel(self):
        self.Actor = Actor(WIDTH=self.WIDTH, HEIGHT=self.HEIGHT, CHARS_COUNT=self.CHARS_COUNT).buildModel()
        self.Critic = Critic(WIDTH=self.WIDTH, HEIGHT=self.HEIGHT, CHARS_COUNT=self.CHARS_COUNT).buildModel()
        self.Critic.compile(loss="mse", optimizer="Adam")
        self.Critic.trainable = False
        imgIn = Input(shape=(256, 256, 3))
        regIn = Input(shape=(8))
        memIn = Input(shape=(8))
        reg2In = Input(shape=(8))
        mem2In = Input(shape=(8))
        nameIn = [Input(shape=(self.CHARS_COUNT)) for _ in range(6)]
        mesIn = Input(shape=(self.CHARS_COUNT))
        seedIn = Input(shape=(100))
        actorAction = self.Actor([imgIn, [regIn, memIn, reg2In, mem2In], [nameIn, mesIn], seedIn])
        valid = self.Critic([[imgIn, [regIn, memIn, reg2In, mem2In], [nameIn, mesIn]], actorAction])
        self.Combined = Model(inputs=[imgIn, [regIn, memIn, reg2In, mem2In], [nameIn, mesIn], seedIn], outputs=[valid])
        self.Combined.compile(loss="mse", optimizer="Adam")

    def convFrame(self, ld, reward):
        inpdata = []
        inpdata.append(np.array([self.convBit(ld["input"]["mem"]["reg"])]))
        inpdata.append(np.array([ld["input"]["mem"]["data"]]))
        inpdata.append(np.array([self.convBit(ld["input"]["mem"]["reg2"])]))
        inpdata.append(np.array([ld["input"]["mem"]["data2"]]))
        inpdata.append(np.array([self.convName(ld["input"]["chat"]["name"])]))
        inpdata.append(np.array([self.convChar(ld["input"]["chat"]["message"])]))
        inpdata.append(np.array([ld["output"]["keyboard"]]))
        inpdata.append(np.array([ld["output"]["mouse"]["dir"]]))
        inpdata.append(np.array([ld["output"]["mouse"]["button"]]))
        inpdata.append(np.array([self.convBit(ld["output"]["mem"]["save"])]))
        inpdata.append(np.array([ld["output"]["mem"]["mem"]]))
        inpdata.append(np.array([self.convBit(ld["output"]["mem"]["reg"])]))
        inpdata.append(np.array([self.convBit(ld["output"]["mem"]["reg2"])]))
        inpdata.append(np.array([self.convChar(ld["output"]["chat"])]))
        inpdata.append(np.array([reward]))
        return inpdata

    def getBit(self, value: int, bit: int) -> int:
        return value >> bit & 0b1

    def convBit(self, value: int):
        return np.array([self.getBit(value, i) for i in range(7, -1, -1)])

    def checkCount(self):
        return len(self.learnFramesBuffer)

    def check(self):
        listIDs = list(self.videoFrames.keys())
        listIDs.extend(list(self.moveFrames.keys()))
        ids = [id for id in set(listIDs) if listIDs.count(id) == 2]
        learnFrameCount = len(self.learnFramesBuffer)

        if len(ids) >= 10 and not self.CHECK_PROCESSING and not self.TRAINING:
            self.CHECK_PROCESSING = True
            counts = []
            idsCopy = ids.copy()
            for i in range(len(ids)):
                id = ids[i]
                count = len(self.moveFrames[id]["data"])
                if count >= 2:
                    counts.append(count)
                    continue
                self.videoFrames.pop(id)
                self.moveFrames.pop(id)
                idsCopy.remove(id)
            ids = idsCopy.copy()
            if len(counts) > 0:
                for id in ids:
                    data = self.moveFrames[id]
                    healthData = [min(data["data"][i]["health"] * (1 if not (i + 1) % 10 == 0 else 1.25 if not (i + 1) % 100 == 0 else 1.5), 20) for i in range(len(data["data"]))]
                    rewardEst = np.array([sum(healthData[dp:])/(len(healthData)-dp) for dp in range(len(healthData))]).reshape(len(healthData), 1) / 20
                    for i in range(len(data["data"])):
                        daf = self.convFrame(data["data"][i], rewardEst[i])
                        img = self.videoFrames[id][i]
                        self.learnFramesBuffer.append({"data": daf, "img": img})
                        if len(self.learnFramesBuffer) > self.LEARN_LIMIT:
                            self.learnFramesBuffer.pop(0)
                    self.moveFrames.pop(id)
                    self.videoFrames.pop(id)
            learnFrameCount = self.checkCount()
            self.CHECK_FIRSTRUN = False
            self.logger.debug("Check done, current total frames: %d/%d" % (learnFrameCount, self.LEARN_LIMIT))
            self.CHECK_PROCESSING = False

        # First Run
        if self.CHECK_FIRSTRUN:
            learnFrameCount = self.checkCount()
            self.logger.debug("First Run, current total frames: %d" % (learnFrameCount))
            self.CHECK_FIRSTRUN = False
            if os.path.exists("models/model.h5") and os.path.exists("models/critic.h5"):
                self.Actor.load_weights("models/model.h5")
                self.Critic.load_weights("models/critic.h5")
        if learnFrameCount >= (self.LEARN_LIMIT * 0.5) and not self.TRAINING:
            self.learn()

    def learn(self):
        batchSize = 32
        if self.TRAINING: return
        self.TRAINING = True
        self.logger.info("Start Learning")

        learnFrames = random.sample(self.learnFramesBuffer, self.LEARN_LIMIT // 4)
        iters = len(learnFrames) // batchSize

        thisEpochs = self.EPOCHS

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
                    self.learn_data.append(frameData)
                    del frameImg, frameData
                x, y, rewardEst = self.convAll()
                x = x[:-1]
                x.extend(y)
                y = rewardEst
                loss = self.Critic.train_on_batch(x, y)
                loss_history.append(loss)
            self.logger.info("Critic Loss: %.6f, %d epochs" % (sum(loss_history)/len(loss_history), epoch))

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
                    self.learn_data.append(frameData)
                    del frameImg, frameData
                x, _, rewardEst = self.convAll()
                realEst = self.Combined.predict(x, verbose=0)
                y = np.maximum(rewardEst, realEst)
                loss = self.Combined.train_on_batch(x, y)
                loss_history.append(loss)
            self.logger.info("Actor Loss: %.6f, %d epochs" % (sum(loss_history)/len(loss_history), epoch))
        tf.keras.backend.clear_session()
        gc.collect()

        self.MODEL_WRITING = True
        self.Actor.save("models/model.h5")
        self.Critic.save("models/critic.h5")
        self.MODEL_WRITING = False

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
        self.TRAINING = False
        self.logger.info("Finish Learning")

    def start(self):
        server = self.ThreadedHTTPServer(("0.0.0.0", 8000), LearnHandler, self)
        server.serve_forever()

if __name__ == '__main__':
    learn = Learn()
    learn.start()
