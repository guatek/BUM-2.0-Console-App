import os 
import sys
import time
import serial
import threading
import numpy as np
from loguru import logger


class SAMD21Controller:

    def __init__(self, port='/dev/ttyACM0', baud=115200):
        self.port = port
        self.baud = baud
        self.new_data = False
        self.pause_thread = False
        self._read_buffer = ''
        self.latest_data = ''
        self.config = ''
        self.stop_thread = False
        self.command_complete = True
        self.last_data_time = time.time()
        self.last_command_time = time.time()

        self._ser = serial.Serial(self.port, self.baud)

        self.t1 = None

    def parse_data(self):
        self.latest_data = self._read_buffer.split('\r')[0].rstrip('\n')
        logger.debug(self.latest_data)
        self._read_buffer = "".join(self._read_buffer.split('\r')[1:]).lstrip('\n')
        self.new_data = False

    def get_config(self):
        self.pause_thread = True
        self._ser.write("!".encode('ascii'))
        time.sleep(0.3)
        self._ser.write(("cfg\r").encode('ascii'))
        buf = ""
        time.sleep(0.1)
        while (self._ser.inWaiting() > 0):
            buf += self._ser.read(self._ser.inWaiting()).decode('ascii') 
        self._ser.write("!".encode('ascii'))

        self.config = buf
        self.pause_thread = False
        logger.debug(buf)

    def direct_comms(self):
        self.pause_thread = True
        self._ser.write("!".encode('ascii'))
        time.sleep(0.1)
        i = ''
        while i != '!':
            i = input('CMD (! to exit)> ')
            if i != '!':
                self._ser.write((i + '\r').encode('ascii'))
                buf = ''
                time.sleep(0.1)
                while (self._ser.inWaiting() > 0):
                    buf += self._ser.read(self._ser.inWaiting()).decode('ascii')
                print(buf)
        self._ser.write("!".encode('ascii'))
        self.pause_thread = False

    def set_cfg_value(self, cfg_name, cfg_value):
        self.pause_thread = True
        cmd = '#SET,' + cfg_name + ',' + cfg_value
        self._ser.write((cmd + "\r").encode('ascii'))
        self.last_command_time = time.time()
        self.pause_thread = False

    def set_cmd(self, cmd_name, cmd_value, cmd_value2=None):
        self.pause_thread = True
        cmd = '#' + cmd_name + ',' + cmd_value
        if cmd_value2 is not None:
            cmd += "," + cmd_value2
        self._ser.write((cmd + "\r").encode('ascii'))
        self.last_command_time = time.time()
        self.pause_thread = False


    def send_command(self, cmd):
        self._ser.write("!".encode('ascii'))
        time.sleep(0.25)
        self._ser.write((cmd + "\r").encode('ascii'))
        time.sleep(0.25)
        self._ser.write("!".encode('ascii'))  

    def send_command_and_confirm(self, cmd):
        self._ser.write("!".encode('ascii'))
        time.sleep(0.25)
        self._ser.write((cmd + "\r").encode('ascii'))
        time.sleep(0.25)
        self._ser.write(("y").encode('ascii'))
        time.sleep(0.25)
        self._ser.write("!".encode('ascii'))  

    def read(self, stop): 
        while (not stop()):
            # Check if incoming bytes are waiting to be read from the serial input 
            # buffer.
            # NB: for PySerial v3.0 or later, use property `in_waiting` instead of
            # function `inWaiting()` below!
            if not self.pause_thread and (self._ser.in_waiting > 0):
                # read the bytes and convert from binary array to ASCII
                self._read_buffer += self._ser.read(self._ser.inWaiting()).decode('ascii') 
                if '$' in self._read_buffer:
                    # Mark any pending commands complete
                    self.last_data_time = time.time()
                if '\r' in self._read_buffer:
                    self.new_data = True
                    self.parse_data()

            # Put the rest of your code you want here
            
            # Optional, but recommended: sleep 10 ms (0.01 sec) once per loop to let 
            # other threads on your PC run during this time. 
            time.sleep(0.1) 


    def run(self):
        logger.debug('starting serial read thread...')
        self.t1 = threading.Thread(target=self.read, args=[lambda: self.stop_thread])
        self.t1.daemon = True
        self.t1.start()

    def stop(self):
        logger.debug('received stop.')
        self.stop_thread = True
        self.t1.join()

    def running_command(self):
        time_since_command = time.time() - self.last_command_time
        time_since_data = time.time() - self.last_data_time
        logger.debug(time_since_data)
        return time_since_command > 1.0 and time_since_data > 0.3
    
    def time_since_data(self):
        return time.time() - self.last_data_time

if __name__ == '__main__':
    d = SAMD21Controller()
    d.run()



