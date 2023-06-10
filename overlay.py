import cv2
import numpy as np

scale_x_offset = 450
scale_color = (200, 200, 250)

# Lens focus data and mapping from diopter to distance / scale
lens_diopter = [-1.960,0.0,2.960] # In diopters
lens_distance = [30, 27, 20] # In distance from viewport
lens_scale = [0.95, 0.99, 1.067] # In um/pixel

lens_distance_map = np.poly1d(np.polyfit(lens_diopter, lens_distance,2))
lens_scale_map = np.poly1d(np.polyfit(lens_diopter, lens_scale,2))

def draw_scale_bar(img, focus_pos):

    x_width = int(100 / lens_scale_map(focus_pos))

    cv2.rectangle(img, 
        (img.shape[1] - scale_x_offset, 20), 
        (img.shape[1] - scale_x_offset  + x_width, 60),
        scale_color,
        thickness = -1
    )

    cv2.putText(
        img = img,
        text = '100 um',
        org = (img.shape[1] - scale_x_offset + x_width + 30, 60),
        fontFace = cv2.FONT_HERSHEY_DUPLEX,
        fontScale = 2,
        color = scale_color,
        thickness = 2
    )