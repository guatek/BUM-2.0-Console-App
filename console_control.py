import os 
import sys
import time
import serial
import threading
import numpy as np
from config.settings import BUM_SETTINGS
from samd21_controller import SAMD21Controller
from loguru import logger


class ConsoleController(SAMD21Controller):

    def __init__(self, port='/dev/ttyACM0', baud=115200):
        super().__init__(port, baud)



