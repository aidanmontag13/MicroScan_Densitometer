import numpy as np
import math
import csv
import time

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

    for i in range(15):
        camera.read() #flush 5 frames

def linearize_frame(frame):

    linear_frame = np.where(
        frame <= 0.04045,
        frame / 12.92,
        np.power(np.maximum(frame + 0.055, 0.0) / 1.055, 2.4)
    )

    return linear_frame


def capture_image(camera, samples=1):

    denoised_image = np.zeros((SENSOR_HEIGHT, SENSOR_WIDTH), np.float32)

    timestamps = []

    for sample in range(samples):
        image = np.zeros((SENSOR_HEIGHT, SENSOR_WIDTH), np.float32)

        ret, frame = camera.read()
        timestamps.append(time.time())

        image = frame[:,:,2].astype(np.float32) / 255

        weight = 1 / (sample + 1)
        denoised_image = cv2.addWeighted(image, weight, denoised_image, (1 - weight), 0)

    denoised_image = linearize_frame(denoised_image)

    mean_timestamp = np.mean(timestamps)

    return denoised_image, mean_timestamp

def visualize_centers(image, centers):
    color_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    
    for center in centers:
        cv2.circle(color_image, (center), 15, (0, 0, 255), thickness=5)

    color_image = cv2.resize(color_image, (720,480))
    
    cv2.imshow("frame", color_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def find_well_centers(image):

    image_8bit = (np.clip(image, 0, 1) * 255).astype(np.uint8)

    params = cv2.SimpleBlobDetector_Params()
    
    # Look for bright blobs
    params.filterByColor = True
    params.blobColor = 255

    # Threshold range
    params.minThreshold = 28
    params.maxThreshold = 256
    params.thresholdStep = 5

    # Blob size
    params.filterByArea = True
    params.minArea = 1500
    params.maxArea = 4500

    # Shape filtering
    params.filterByCircularity = True
    params.minCircularity = 0.5

    params.filterByConvexity = False
    params.filterByInertia = False

    detector = cv2.SimpleBlobDetector_create(params)
    
    ret, centers = cv2.findCirclesGrid(
        image_8bit,
        (12, 8),
        flags=cv2.CALIB_CB_SYMMETRIC_GRID,
        blobDetector=detector
    )

    centers_list = []

    for center in centers:
        x, y = map(int, center[0])
        centers_list.append((x,y))

    return centers_list

def sample_wells(image, well_centers):

    values = []

    for center in well_centers:
        mask = np.zeros(image.shape, dtype=np.uint8)

        cv2.circle(
            mask,
            center,
            10,
            255,
            thickness=-1
        )

        mean_value = cv2.mean(image, mask=mask)[0]

        values.append(mean_value)

    return values

def calculate_densities(samples, calibration_values):

    densities = []

    for sample, calibration in samples, calibration_values:
        density = math.log10(calibration / sample)

        densities.append(density)

    return densities

def sample_densities(camera, well_centers, calibration_values):
    
    image, timestamp = capture_image(camera, samples=1, exposures=1) # capture calibration image
    
    well_values = sample_wells(image, well_centers) #Sample values from each center

    well_densities = calculate_densities(well_values, calibration_values)

    return well_densities, timestamp

def read_well_names():
    with open("resources/well_names.csv", "r", newline="") as file:
        reader = csv.reader(file)
        names = [row[0] for row in reader]

    return names

def write_calibration_csv(well_names, well_centers, well_values):
    with open("calibration.csv", "w", newline="") as file:
        writer = csv.writer(file)

        writer.writerow(["Well", "X", "Y", "Value"])

        for well_name, well_center, well_value in zip(well_names, well_centers, well_values):

            x_value = well_center[0]
            y_value = well_center[1]

            writer.writerow([well_name, x_value, y_value, well_value])

def read_calibration_csv():

    well_names = []
    well_centers = []
    well_values = []

    with open("calibration.csv", "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            well_names.append(row["Well"])
            well_centers.append((int(row["X"]), int(row["Y"])))
            well_values.append(float(row["Value"]))

    return well_names, well_centers, well_values

def calibrate_densitometer(camera):

    well_names = read_well_names() #read well names

    apply_camera_settings(camera, -11, 0) # apply camera settings

    image = capture_image(camera, samples=1, exposures=1) # capture calibration image

    well_centers = find_well_centers(image) #locate well centers

    well_values = sample_wells(image, well_centers) #Sample values from each center

    write_calibration_csv(well_names, well_centers, well_values) # export calibration file

def write_measurement_csv(filename, well_names, densities_list, timestamp_list):
    with open("calibration.csv", "w", newline="") as file:
        writer = csv.writer(file)

        writer.writerow(["Well Name"] + timestamp_list)

        for well_name, densities in zip(well_names, zip(*densities_list)):
            writer.writerow([well_name] + list(densities))

def measure_single_density(filename, camera):

    well_names, well_centers, calibration_values = read_calibration_csv()

    densities_list = []
    timestamp_list = []

    densities, timestamp = sample_densities(camera, well_centers, calibration_values)

    write_measurement_csv(filename, well_names, densities, timestamp)

def measure_densities_over_time(filename, camera, duration, sample_interval):
    duration = duration * 60 # convert from minutes to seconds
    sample_interval = sample_interval * 60

    well_names, well_centers, calibration_values = read_calibration_csv()

    densities_list = []
    timestamp_list = []

    start_time = time.time()
    interval_time = time.time()

    while time.time() - start_time < duration:
        if time.time() - interval_time >= sample_interval:
            densities, timestamp = sample_densities(camera, well_centers, calibration_values)
            densities_list.append(densities)
            timestamp_list.append(timestamp)

            write_measurement_csv(filename, well_names, densities_list, timestamp_list)

            interval_time = time.time()