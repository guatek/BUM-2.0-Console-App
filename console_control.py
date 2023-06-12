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
        # $BUMCTRL,2022-06-09 14:32:40.344,29.370,102.690,17.92,16.01,40.48,16.01,0.92,12.09,19.51,11.96,13.54,12.08,5.95,100.0
        self.data_fields = ['name',
                            'timestamp',
                            'temperature',
                            'pressure',
                            'humidity',
                            'voltage_sys',
                            'power_sys',
                            'voltage_probe',
                            'power_probe',
                            'voltage_orin',
                            'power_orin',
                            'voltage_disp',
                            'power_disp',
                            'voltage_cam',
                            'power_cam',
                            'state_of_charge']
        self.data_list = ['name','timestamp',0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]

        self.system_time_set = False


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
                for i in [2,3,4,5,6,7,8,9,10,11,12,13,14,15]:
                    self.data_list[i] = float(tokens[i])
                # Set system time if not set yet
                if not self.system_time_set:
                    os.system('sudo timedatectl set-ntp no')
                    os.system('sudo timedatectl set-time ' + self.data_list[1])
                    self.system_time_set = True

        except Exception as e:
            print(e)
        self.new_data = False

    def get_latest_data(self):
        return self.data_list
    

if __name__=='__main__':
    pc = ConsoleController(port='/dev/ttyUSB1')
    pc.run()
    while True:
        c = input()
        if c == 'd':
            print(pc.get_latest_data())
        if c =='e':
            break



