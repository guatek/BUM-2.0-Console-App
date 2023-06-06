import cv2
import numpy as np

img = np.zeros((512,512,3))

while(1):
    cv2.imshow('img',img)
    k = cv2.waitKey(100)
    if k==27:    # Esc key to stop
        break
    elif k==-1:  # normally -1 returned,so don't print it
        continue
    else:
        print(k) # else print its value


"""
114 = Rec
109 = Menu
119 = Up
115 = Down
105 = Mode
101 = Enter
100 = right
97 = left
"""