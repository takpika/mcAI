from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, Input, Conv2D, Flatten, Concatenate, MaxPooling2D, BatchNormalization, Dropout
from tensorflow.keras.losses import CategoricalCrossentropy
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.backend import clear_session
import numpy as np
from random import random
import os

class mcAI():
    def __init__(self, WIDTH, HEIGHT, CHARS_COUNT, logger):
        os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
        self.WIDTH = WIDTH
        self.HEIGHT = HEIGHT
        self.CHARS_COUNT = CHARS_COUNT
        self.logger = logger
        self.make_model()

    def clearSession(self):
        clear_session()

    def charEncoder(self):
        inp = Input(shape=(self.CHARS_COUNT))
        out = Dense(2, activation="relu")(inp)
        return Model([inp], out)

    def nameEncoder(self):
        name_chars = [self.charEncoder() for i in range(6)]
        name_chars_o = [c.output for c in name_chars]
        name_chars_i = [c.input for c in name_chars]
        hid = Concatenate()(name_chars_o)
        out = Dense(16, activation="relu")(hid)
        return Model(name_chars_i, out)

    def chatEncoder(self):
        name = self.nameEncoder()
        char = self.charEncoder()
        hid = Concatenate()([name.output, char.output])
        out = Dense(16, activation="relu")(hid)
        return Model([name.input, char.input], out)

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

    def build_videoEncoder(self):
        inp = Input(shape=(self.HEIGHT, self.WIDTH, 3))
        hid = Conv2D(64, kernel_size=4, padding="same", activation="relu")(inp)
        hid = MaxPooling2D((2,2))(hid)
        hid = BatchNormalization()(hid)
        hid = Conv2D(128, kernel_size=4, padding="same", activation="relu")(hid)
        hid = MaxPooling2D((2,2))(hid)
        hid = BatchNormalization()(hid)
        hid = Conv2D(256, kernel_size=4, padding="same", activation="relu")(hid)
        hid = MaxPooling2D((2,2))(hid)
        hid = BatchNormalization()(hid)
        hid = Flatten()(hid)
        out = Dense(16, activation="relu")(hid)
        return Model([inp], out)

    def build_hidden(self):
        video = self.build_videoEncoder()
        mem = self.memEncoder()
        chat = self.chatEncoder()
        seed = Input(shape=(100))
        hid = Concatenate()([video.output, mem.output, chat.output, seed])
        hid = Dropout(0.2)(hid)
        hid = Dense(64, activation="relu")(hid)
        hid = Dense(32, activation="relu")(hid)
        out = Dense(16, activation="relu")(hid)
        return Model([video.input, mem.input, chat.input, seed], out)

    def build_controlDecoder(self):
        inp = Input(shape=(16))
        hid = Dense(64, activation="relu")(inp)
        hid = Dense(32, activation="relu")(hid)
        out = Dense(17, activation="relu")(hid)
        return Model([inp], out)

    def build_mouseDecoder(self):
        inp = Input(shape=(16))
        hid = Dense(64, activation="relu")(inp)
        hid = Dense(32, activation="relu")(hid)
        out_dir = Dense(2, activation="relu")(hid)
        out_lr = Dense(2, activation="relu")(hid)
        return Model([inp], [out_dir, out_lr])

    def build_memDecoder(self):
        inp = Input(shape=(16))
        hid = Dense(64, activation="relu")(inp)
        hid = Dense(32, activation="relu")(hid)
        out_save_reg = Dense(8, activation="relu")(hid)
        out_data = Dense(8, activation="relu")(hid)
        out_set_reg = Dense(8, activation="relu")(hid)
        out_set_reg2 = Dense(8, activation="relu")(hid)
        return Model([inp], [out_save_reg, out_data, out_set_reg, out_set_reg2])

    def build_chatDecoder(self):
        inp = Input(shape=(16))
        hid = Dense(64, activation="relu")(inp)
        hid = Dense(32, activation="relu")(hid)
        out = Dense(self.CHARS_COUNT, activation="softmax")(hid)
        return Model([inp], out)

    def build_Model(self):
        hid = self.build_hidden()
        ctrl = self.build_controlDecoder()(hid.output)
        mouse = self.build_mouseDecoder()(hid.output)
        mem = self.build_memDecoder()(hid.output)
        chat = self.build_chatDecoder()(hid.output)
        return Model([hid.input], [ctrl, mouse, mem, chat])

    def make_model(self):
        self.model = self.build_Model()
        self.loss = CategoricalCrossentropy()
        self.optimizer = Adam()
        self.model.compile(optimizer=self.optimizer, loss="mae", metrics=["accuracy"])

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