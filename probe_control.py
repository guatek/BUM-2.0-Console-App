import os 
import sys
import time
import serial
import threading
import numpy as np
from config.settings import BUM_SETTINGS
from samd21_controller import SAMD21Controller
from loguru import logger


class ProbeController(SAMD21Controller):

    def __init__(self, port='/dev/ttyACM0', baud=115200):
        super().__init__(port, baud)
        self.data_fields = ['name','timestamp','temperature','humidity','pressure','voltage','power']
        self.data_list = ['name','timestamp',0.0,0.0,0.0,0.0,0.0]


    def parse_data(self):
        self.latest_data = self._read_buffer.split('\r')[0].rstrip('\n')
        #logger.debug(self.latest_data)
        self._read_buffer = "".join(self._read_buffer.split('\r')[1:]).lstrip('\n')
        try:
            tokens = self.latest_data.split(',')
            if len(tokens) != len(self.data_fields):
                logger.warning("Error parsing data string: " + self.latest_data)
            else:
                self.data_list[0] = tokens[0]
                self.data_list[1] = tokens[1]
                for i in [2,3,4,5,6]:
                    self.data_list[i] = float(tokens[i])
        except Exception as e:
            print(e)
        self.new_data = False

    def get_latest_data(self):
        return self.data_list
    

if __name__=='__main__':
    pc = ProbeController(port='/dev/ttyUSB0')
    pc.run()
    while True:
        c = input()
        if c == 'd':
            print(pc.get_latest_data())
        if c =='e':
            break