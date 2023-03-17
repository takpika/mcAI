from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, Input, Flatten, Concatenate
from tensorflow.keras.backend import clear_session
import numpy as np
from random import random
import os
from . import image, text, control

def clearSession():
    clear_session()

class Actor():
    def __init__(self, WIDTH, HEIGHT, CHARS_COUNT, logger):
        os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
        self.WIDTH = WIDTH
        self.HEIGHT = HEIGHT
        self.CHARS_COUNT = CHARS_COUNT
        self.logger = logger
        self.encoder = image.ImageEncoder()
        self.encoder.model.trainable = False
        self.charencoder = text.CharEncoder(CHARS_COUNT)
        self.charencoder.model.trainable = False
        self.nameencoder = text.NameEncoder(CHARS_COUNT)
        self.nameencoder.model.trainable = False
        self.keyboarddecoder = control.KeyboardDecoder()
        self.keyboarddecoder.model.trainable = False
        self.mousedecoder = control.MouseDecoder()
        self.mousedecoder.model.trainable = False
        self.make_model()

    def chatEncoder(self):
        name = self.nameencoder.model
        hid = Concatenate()([name.output, self.charencoder.model.output])
        out = Dense(16, activation="relu")(hid)
        return Model([name.input, self.charencoder.model.input], out)

    def memEncoder(self):
        reg = Input(shape=(8))
        data = Input(shape=(8))
        reg2 = Input(shape=(8))
        data2 = Input(shape=(8))
        hid = Concatenate()([reg, data])
        hid2 = Concatenate()([reg2, data2])
        hid = Concatenate()([hid, hid2])
        out = Dense(16, activation="relu")(hid)
        return Model([reg, data, reg2, data2], out)

    def build_hidden(self):
        video = self.encoder.model
        mem = self.memEncoder()
        chat = self.chatEncoder()
        seed = Input(shape=(100))
        video_hid = Flatten()(video.output)
        hid = Concatenate()([video_hid, mem.output, chat.output, seed])
        hid = Dense(32, activation="relu")(hid)
        hid = Dense(64, activation="relu")(hid)
        hid = Dense(64, activation="relu")(hid)
        out = Dense(32, activation="relu")(hid)
        return Model([video.input, mem.input, chat.input, seed], out)

    def build_memDecoder(self):
        inp = Input(shape=(16))
        hid = Dense(64, activation="relu")(inp)
        hid = Dense(32, activation="relu")(hid)
        out_save_reg = Dense(8, activation="sigmoid")(hid)
        out_data = Dense(8, activation="relu")(hid)
        out_set_reg = Dense(8, activation="sigmoid")(hid)
        out_set_reg2 = Dense(8, activation="sigmoid")(hid)
        return Model([inp], [out_save_reg, out_data, out_set_reg, out_set_reg2])

    def build_chatDecoder(self):
        inp = Input(shape=(16))
        hid = Dense(64, activation="relu")(inp)
        hid = Dense(32, activation="relu")(hid)
        out = Dense(self.CHARS_COUNT, activation="softmax")(hid)
        return Model([inp], out)

    def build_Model(self):
        hid = self.build_hidden()
        ctrl = self.keyboarddecoder.model(Dense(16, activation="relu")(hid.output))
        mouse = self.mousedecoder.model(Dense(16, activation="relu")(hid.output))
        mem = self.build_memDecoder()(Dense(16, activation="relu")(hid.output))
        chat = self.build_chatDecoder()(Dense(16, activation="relu")(hid.output))
        return Model([hid.input], [ctrl, mouse, mem, chat])

    def make_model(self):
        self.model = self.build_Model()
        self.model.compile(optimizer="Adam", loss="mae", metrics=["accuracy"])

    def make_input(self, x_img, x_reg, x_mem, x_reg2, x_mem2, x_name, x_mes, count):
        return [
            x_img.reshape((count,self.HEIGHT,self.WIDTH,3)),
            x_reg.reshape((count,8)),
            x_mem.reshape((count,8)),
            x_reg2.reshape((count,8)),
            x_mem2.reshape((count,8)),
            x_name[0].reshape((count,self.CHARS_COUNT)),
            x_name[1].reshape((count,self.CHARS_COUNT)),
            x_name[2].reshape((count,self.CHARS_COUNT)),
            x_name[3].reshape((count,self.CHARS_COUNT)),
            x_name[4].reshape((count,self.CHARS_COUNT)),
            x_name[5].reshape((count,self.CHARS_COUNT)),
            x_mes.reshape((count,self.CHARS_COUNT)),
            np.random.random((count, 100))
        ]
    
    def predict(self, *args, **kwargs):
        result = self.model.predict(args, kwargs, verbose=0)
        clear_session()
        return result
    
class Critic:
    def __init__(self, WIDTH, HEIGHT, CHARS_COUNT, logger):
        os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
        self.WIDTH = WIDTH
        self.HEIGHT = HEIGHT
        self.CHARS_COUNT = CHARS_COUNT
        self.logger = logger
        self.encoder = image.ImageEncoder()
        self.encoder.model.trainable = False
        self.charencoder = text.CharEncoder(CHARS_COUNT)
        self.charencoder.model.trainable = False
        self.nameencoder = text.NameEncoder(CHARS_COUNT)
        self.nameencoder.model.trainable = False
        self.keyboardencoder = control.KeyboardEncoder()
        self.keyboardencoder.model.trainable = False
        self.mouseencoder = control.MouseEncoder()
        self.mouseencoder.model.trainable = False
        self.actorcharencoder = text.CharEncoder(CHARS_COUNT)
        self.actorcharencoder.model.trainable = False
        self.make_model()

    def chatEncoder(self):
        name = self.nameencoder.model
        hid = Concatenate()([name.output, self.charencoder.model.output])
        out = Dense(16, activation="relu")(hid)
        return Model([name.input, self.charencoder.model.input], out)

    def memEncoder(self):
        reg = Input(shape=(8))
        data = Input(shape=(8))
        reg2 = Input(shape=(8))
        data2 = Input(shape=(8))
        hid = Concatenate()([reg, data])
        hid2 = Concatenate()([reg2, data2])
        hid = Concatenate()([hid, hid2])
        out = Dense(16, activation="relu")(hid)
        return Model([reg, data, reg2, data2], out)
    
    def buildDataInput(self):
        videoIn = self.encoder.model
        memIn = self.memEncoder()
        chatIn = self.chatEncoder()
        videoHid = Flatten()(videoIn.output)
        hid = Concatenate()([videoHid, memIn.output, chatIn.output])
        hid = Dense(32, activation="relu")(hid)
        return Model([videoIn.input, memIn.input, chatIn.input], hid)
    
    def buildActorInput(self):
        ctrl = self.keyboardencoder.model
        mouse = self.mouseencoder.model
        mem = self.memEncoder()
        char = self.actorcharencoder.model
        hid = Concatenate()([ctrl.output, mouse.output, mem.output, char.output])
        hid = Dense(32, activation="relu")(hid)
        return Model([ctrl.input, mouse.input, mem.input, char.input], hid)
    
    def buildModel(self):
        dataIn = self.buildDataInput()
        actorIn = self.buildActorInput()
        hid = Concatenate()([dataIn.output, actorIn.output])
        hid = Dense(64, activation="relu")(hid)
        hid = Dense(64, activation="relu")(hid)
        hid = Dense(64, activation="relu")(hid)
        out = Dense(1, activation="relu")(hid)
        return Model([dataIn.input, actorIn.input], out)
    
    def make_model(self):
        self.model = self.buildModel()
        self.model.compile(optimizer="Adam", loss="mae")