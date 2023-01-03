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
        model.compile(optimizer="Adam", loss="mae")
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
