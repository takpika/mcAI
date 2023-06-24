import numpy as np
from time import time
import random
from PIL import Image

class GameSession:
    def __init__(self, sessionID: str, parent):
        self.parent = parent
        self.sessionID = sessionID
        self.sendMessageData = ""
        self.memory: np.ndarray = np.random.random((2**8, 8))
        self.randomSeed = 0.5 * random.random()
        self.moveDis = [0, 0]
        self.checkedMesID = -1
        self.unreadMessages = []
        self.readMessageCharPos = 0
        self.readMemRegs = [0x0, 0x0]
        self.playStartTime = -1
        self.playFrameCounts = 0
        self.nextHunger = time()
        self.jumpCount = 0
        self.beforeHp, self.criticalHp = 8, 999999
        self.editChar = ""
        self.inScreen = False
        self.beforeKeys = [False for _ in parent.KEYS]
        self.headTopBtmTime, self.headProcessed = -1, False
        self.positionHistory = []
        self.afkStartTime, self.afkProcessed = -1, False
        self.newbie, self.newbieDamage, self.newbieDamageChecked = True, False, False