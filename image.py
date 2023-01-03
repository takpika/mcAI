from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.layers import Dense, Input, Conv2D, MaxPooling2D, BatchNormalization, UpSampling2D
import numpy as np

class ImageVAE():
    def __init__(self):
        self.encoder = ImageEncoder()
        self.decoder = ImageDecoder()
        self.model = self.build_model()

    def build_model(self):
        model = Sequential()
        model.add(self.encoder.model)
        model.add(self.decoder.model)
        model.compile(optimizer="Adam", loss="mae")
        return model

class ImageEncoder():
    def __init__(self, path=None):
        self.model = self.build_model()
        if path != None:
            self.model.load_weights(path)

    def build_model(self):
        inp = Input(shape=(256, 256, 3))
        #256, 256, 16
        hid = Conv2D(16, kernel_size=2, padding="same", activation="relu")(inp)
        hid = MaxPooling2D((2,2))(hid)
        #128, 128, 32
        hid = Conv2D(32, kernel_size=2, padding="same", activation="relu")(hid)
        hid = MaxPooling2D((2,2))(hid)
        #64, 64, 64
        hid = Conv2D(64, kernel_size=2, padding="same", activation="relu")(hid)
        hid = MaxPooling2D((2,2))(hid)
        #32, 32, 128
        out = Conv2D(128, kernel_size=2, padding="same", activation="relu")(hid)
        return Model(inp, out)

class ImageDecoder():
    def __init__(self, path=None):
        self.model = self.build_model()
        if path != None:
            self.model.load_weights(path)

    def build_model(self):
        inp = Input(shape=(32, 32, 128))
        #64, 64, 64
        hid = UpSampling2D((2,2))(inp)
        hid = Conv2D(64, kernel_size=2, padding="same", activation="relu")(hid)
        #128, 128, 32
        hid = UpSampling2D((2,2))(hid)
        hid = Conv2D(32, kernel_size=2, padding="same", activation="relu")(hid)
        #256, 256, 16
        hid = UpSampling2D((2,2))(hid)
        hid = Conv2D(16, kernel_size=2, padding="same", activation="relu")(hid)
        out = Conv2D(3, kernel_size=2, padding="same", activation="relu")(hid)
        return Model(inp, out)