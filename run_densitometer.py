import time
import numpy as np
import math
import os

import cv2
from cv2_enumerate_cameras import enumerate_cameras

    
SENSOR_WIDTH = 2592
SENSOR_HEIGHT = 1944

def find_arducam_camera():
    for cam in enumerate_cameras(cv2.CAP_DSHOW):
        if "arducam".lower() in cam.name.lower():
            camera = cv2.VideoCapture(cam.index, cv2.CAP_DSHOW)
            return camera

    print("Error: No arducam camera found")
    return None
    
def apply_camera_settings(camera, exposure, gain):
    
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUY2'))

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, SENSOR_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, SENSOR_HEIGHT)

    camera.set(cv2.CAP_PROP_AUTO_WB, 0)

    camera.set(cv2.CAP_PROP_SHARPNESS, 0)

    camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    camera.set(cv2.CAP_PROP_EXPOSURE, exposure)
    camera.set(cv2.CAP_PROP_GAIN, gain)
    
    camera.read() #flush 1 frame

def linearize_frame(frame):

    linear_frame = np.where(
        frame <= 0.04045,
        frame / 12.92,
        np.power(np.maximum(frame + 0.055, 0.0) / 1.055, 2.4)
    )

    return linear_frame


def capture_image(camera, samples=1):

    denoised_frame = np.zeros((SENSOR_HEIGHT, SENSOR_WIDTH, 3), np.float32)

    for sample in range(samples):
        print("capturing sample ", sample + 1)

        ret, frame = camera.read()
        
        frame = frame[:,:,:].astype(np.float32) / 255

        weight = 1 / (sample + 1)
        denoised_frame = cv2.addWeighted(frame, weight, denoised_frame, (1 - weight), 0)

    denoised_frame = linearize_frame(denoised_frame)

    return denoised_frame


def main():
    camera = find_arducam_camera()

    apply_camera_settings(camera, -2, 0)

    image = capture_image(camera, samples=10)

    frame = (image * 255).astype(np.uint8)

    frame = cv2.resize(frame, (720,480))

    print("max code value", np.max(frame))

    cv2.imshow("frame", frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
        
if __name__ == "__main__":
    main()