import cv2
import time
import numpy as np

from loguru import logger

def command_to_pc(cmd, pc=None):

    logger.debug(cmd)

    tokens = cmd.split(',')

    if pc is None:
        return

    if len(tokens) < 2:
        return
    
    # Move lens
    if tokens[0].lower() == 'move':
        try:
            pc.set_cmd("movelens",tokens[1],tokens[2])
        except:
            pass
    # Step Lens
    elif tokens[0].lower() == 'step':
        try:
            pc.set_cmd("steplens",tokens[1])
        except:
            pass
    # Do White Flash
    elif tokens[0].lower() == 'white':
        try:
            pc.set_cfg_value('imagingmode', '0')
            time.sleep(0.1)
            pc.set_cfg_value('whiteflash', tokens[1])
        except:
            pass
    # Do Violet Flash
    elif tokens[0].lower() == 'violet':
        try:
            pc.set_cfg_value('imagingmode', '1')
            time.sleep(0.1)
            pc.set_cfg_value('uvflash', tokens[1])
        except:
            pass
    elif tokens[0].lower() == 'delay':
        time.sleep(float(tokens[1])/1000)

class ButtonMacro:

    def __init__(self, pc):
        self.pc = pc
        self.command_list = []
        self.command_index = 0
        self.last_command = ''
        self.last_command_time = 0
        self.done = False

    def update(self):
        cmd = ''
        if not self.done and self.command_index < len(self.command_list):
            
            # Rate limit commands to 1 Hz
            if time.time() - self.last_command_time > 5.0:
                self.last_command = self.command_list[self.command_index]
                command_to_pc(self.last_command, self.pc)
                self.last_command_time = time.time()
                self.command_index += 1
            cmd = self.last_command

        else:
            self.done = True
            self.command_index = 0
        return cmd

class ButtonOneMacro(ButtonMacro):

    def __init__(self, pc):
        super().__init__(pc)

        # Add commands here
        self.command_list.append('move,-1.99,0.05')
        self.command_list.append('move,2.99,0.05')


