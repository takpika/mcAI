from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.layers import Dense, Input, Concatenate
import numpy as np

class CharVAE():
    def __init__(self, charsCount):
        self.encoder = CharEncoder(charsCount)
        self.decoder = CharDecoder(charsCount)
        self.model = self.build_model()

    def build_model(self):
        model = Sequential()
        model.add(self.encoder.model)
        model.add(self.decoder.model)
        model.compile(optimizer="Adam", loss="categorical_crossentropy")
        return model

class CharEncoder():
    def __init__(self, charsCount):
        self.charsCount = charsCount
        self.model = self.build_model()

    def build_model(self):
        inp = Input(shape=(self.charsCount))
        out = Dense(2, activation="relu")(inp)
        return Model(inp, out, name="char_encoder")

class CharDecoder():
    def __init__(self, charsCount):
        self.charsCount = charsCount
        self.model = self.build_model()

    def build_model(self):
        inp = Input(shape=(2))
        out = Dense(self.charsCount, activation="softmax")(inp)
        return Model(inp, out, name="char_decoder")

class NameVAE():
    def __init__(self, charsCount):
        self.encoder = NameEncoder(charsCount)
        self.decoder = NameDecoder(charsCount)
        self.model = self.build_model()

    def build_model(self):
        out = self.decoder.model(self.encoder.model.output)
        model = Model(self.encoder.model.input, out)
        model.compile(optimizer="Adam", loss="mae")
        return model

class NameEncoder():
    def __init__(self, charsCount):
        self.charsCount = charsCount
        self.chars = [CharEncoder(charsCount) for i in range(6)]
        for c in self.chars:
            c.model.trainable = False
        self.model = self.build_model()

    def build_model(self):
        name_chars_o = [c.model.output for c in self.chars]
        hid = Concatenate()(name_chars_o)
        out = Dense(16, activation="relu")(hid)
        return Model([c.model.input for c in self.chars], out, name="name_encoder")

class NameDecoder():
    def __init__(self, charsCount):
        self.charsCount = charsCount
        self.chars = [CharDecoder(charsCount) for i in range(6)]
        for c in self.chars:
            c.model.trainable = False
        self.model = self.build_model()

    def build_model(self):
        inp = Input(shape=(16))
        charHid = [Dense(16, activation="relu")(inp) for i in range(6)]
        name_chars_o = [self.chars.model[i](charHid[i]) for i in range(6)]
        return Model(inp, name_chars_o, name="name_decoder")
