from threading import Thread
import os
import cv2
import time
from collections import deque
from loguru import logger

import threading
import time
from collections import deque

class VideoRecorder(threading.Thread):
    def __init__(self, frame_width=3840, frame_height=2160, frame_rate=20):
        threading.Thread.__init__(self)
        self.q = deque()

        timestr = time.strftime("%Y%m%d-%H%M%S")
        self.video_file = os.path.join('/','NVMEDATA',timestr + '.mp4')

        # Default resolutions of the frame are obtained (system dependent)
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.frame_rate = frame_rate
        self.frame_number = 0

        #gst_pipeline = 'appsrc ! video/x-raw,format=BGR ! queue ! videoconvert ! x264enc threads=4 ! h264parse ! qtmux ! filesink'
        gst_pipeline = 'appsrc ! video/x-raw, format=BGR ! queue ! videoconvert ! video/x-raw,format=RGBA ! nvvidconv ! nvv4l2h265enc bitrate=8000000 ! video/x-h265, streamformat=(string)byte-stream ! h265parse ! qtmux ! filesink'

        gst_pipeline = gst_pipeline + ' location=' + self.video_file
        logger.debug(gst_pipeline)
        # Set up codec and output video settings
        #self.codec = cv2.VideoWriter_fourcc('M','J','P','G')
        #self.codec = cv2.VideoWriter_fourcc(*'hvc1')
        self.output_video = cv2.VideoWriter(gst_pipeline, 0, self.frame_rate, (self.frame_width, self.frame_height), True)

        self.stop_recording = False

        self.start()

    def run(self):
        logger.debug('Starting recorder thread...')
        while not self.stop_recording or self.q:
            try:
                self.save_frame(self.q.popleft())
                logger.debug('Saving frame: ' + self.video_file + ' : ' + str(self.frame_number))
                self.frame_number += 1
            except IndexError:
                #logger.debug("Queue is empty.")
                time.sleep(0.01)
                pass
            
        logger.debug('Ended recorder thread...')
        self.output_video.release()

    def add_frame(self, frame):
        logger.debug("Adding Frame...")
        self.q.append(frame)

    def end_recording(self):
        logger.debug('Stopping recorder thread...')
        self.stop_recording = True

    def save_frame(self, frame):
        # Save obtained frame into video output file
        self.output_video.write(frame)
