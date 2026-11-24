import microscan_densitometer as md

import argparse
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="Calculate intrinsic camera parameters.")
    parser.add_argument(
        "--filename",
        type=str,
        default=None,
        help="Name of the exported csv file"
    )
    parser.add_argument(
        "--test-duration",
        type=float,
        default=None,
        help="Duration of the test in minutes"
    )
    parser.add_argument(
        "--sample-interval",
        type=float,
        default=1.0,
        help="Time interval between samples"
    )

    args = parser.parse_args()

    if not args.filename:
        timestamp = datetime.now().strftime("%d, %H:%M:%S")
        filename = "measurement" + timestamp

    else:
        filename = args.filename
    
    camera = md.find_arducam_camera

    if not args.test_duration:
        md.measure_single_density(filename, camera)

    else:
        md.measure_densities_over_time(filename, camera, args.test_duration, args.sample_interval)

if __name__ == "__main__":
    main()
