import cv2
import time

FPS_SMOOTHING = 0.9

WINDOW_NAME = 'BUM2.0'

cv2.namedWindow(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

cap = cv2.VideoCapture('/home/bum/test.mp4')
fps = 0.0
prev = time.time()
while True:
    now = time.time()
    fps = (fps*FPS_SMOOTHING + (1/(now - prev))*(1.0 - FPS_SMOOTHING))
    prev = now

    print("fps: {:.1f}".format(fps))

    got, frame = cap.read()
    if got:
        cv2.imshow(WINDOW_NAME, frame)
    if (cv2.waitKey(2) == 27):
        break