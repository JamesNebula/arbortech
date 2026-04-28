import laspy
import numpy as np
from pathlib import Path

def create_minimal_laz(output_path: str):
    x_coords = np.array([10.0, 20.0, 30.0])
    y_coords = np.array([10.0, 20.0, 30.0])
    z_coords = np.array([5.0, 15.0, 25.0])

    hdr = laspy.LasHeader(version="1.4", point_format=6)

    hdr.scales = np.array([0.1, 0.1, 0.1])
    hdr.offsets = [np.min(x_coords), np.min(y_coords), np.min(z_coords)]

    las = laspy.LasData(hdr)
    las.x = x_coords
    las.y = y_coords
    las.z = z_coords

    las.write(output_path)


if __name__ == "__main__":
    create_minimal_laz("test_file.las")
    