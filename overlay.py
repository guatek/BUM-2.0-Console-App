import cv2
import shutil
import numpy as np

scale_x_offset = 450
scale_color = (200, 220, 200)
sensor_color = (200, 220, 200)

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

def draw_sensor_status(img, latest_sensor_data):

    sys_temp = latest_sensor_data[2]
    sys_hum = latest_sensor_data[4]
    batt_charge = latest_sensor_data[15]

    disk_usage = shutil.disk_usage('/NVMEDATA')
    sensor_text = "Temp: " + '{:.2f}'.format(sys_temp) 
    sensor_text += " C, Humidity: " + '{:.2f}'.format(sys_hum) 
    sensor_text += " %, Battery: " +  '{:.2f}'.format(batt_charge) + " %"
    sensor_text += " Storage: " + '{:.1f}'.format(100*(float(disk_usage[2]) / float(disk_usage[1]+disk_usage[2]))) + " %"

    cv2.putText(
        img = img,
        text = sensor_text,
        org = (50, 60),
        fontFace = cv2.FONT_HERSHEY_DUPLEX,
        fontScale = 2,
        color = sensor_color,
        thickness = 2
    )
