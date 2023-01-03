from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.layers import Dense, Input, Concatenate
import numpy as np

class KeyboardVAE():
    def __init__(self):
        self.encoder = KeyboardEncoder()
        self.decoder = KeyboardDecoder()
        self.model = self.build_model()

    def build_model(self):
        model = Sequential()
        model.add(self.encoder.model)
        model.add(self.decoder.model)
        model.compile(optimizer="Adam", loss="mae")
        return model

class KeyboardEncoder():
    def __init__(self):
        self.model = self.build_model()

    def build_model(self):
        inp = Input(shape=(17))
        hid = Dense(32, activation="relu")(inp)
        out = Dense(16, activation="relu")(hid)
        return Model(inp, out, name="keyboard_encoder")

class KeyboardDecoder():
    def __init__(self):
        self.model = self.build_model()

    def build_model(self):
        inp = Input(shape=(16))
        hid = Dense(32, activation="relu")(inp)
        out = Dense(17, activation="relu")(hid)
        return Model(inp, out, name="keyboard_decoder")

class MouseVAE():
    def __init__(self):
        self.encoder = MouseEncoder()
        self.decoder = MouseDecoder()
        self.model = self.build_model()

    def build_model(self):
        out = self.decoder.model(self.encoder.model.output)
        model = Model(self.encoder.model.input, out)
        model.compile(optimizer="Adam", loss="mae")
        return model

class MouseEncoder():
    def __init__(self):
        self.model = self.build_model()

    def build_model(self):
        inp_dir = Input(shape=(2))
        inp_btn = Input(shape=(2))
        hid = Concatenate()([inp_dir, inp_btn])
        hid = Dense(32, activation="relu")(hid)
        out = Dense(16, activation="relu")(hid)
        return Model([inp_dir, inp_btn], out, name="mouse_encoder")

class MouseDecoder():
    def __init__(self):
        self.model = self.build_model()

    def build_model(self):
        inp = Input(shape=(16))
        hid = Dense(32, activation="relu")(inp)
        out_dir = Dense(2, activation="relu")(hid)
        out_btn = Dense(2, activation="relu")(hid)
        return Model(inp, [out_dir, out_btn], name="mouse_decoder")