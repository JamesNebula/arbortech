# verify_test_file.py
import laspy

las = laspy.read("test_file.las")
print(f"Version: {las.header.version}")
print(f"Point format: {las.header.point_format.id}")
print(f"Point count: {len(las.points)}")
print(f"X range: {las.x.min()} to {las.x.max()}") # type: ignore