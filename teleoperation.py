import openvr
import time
from time import sleep
import math

SAMPLING_RATE = 120 

def precise_wait(duration):
    """
    Wait for a specified duration with high precision.
    Uses sleep for durations >= 1 ms, otherwise uses busy-wait.
    """
    now = time.time()
    end = now + duration
    if duration >= 0.001:
        sleep(duration)
    while now < end:
        now = time.time()

class VRSystemManager:
    def __init__(self):
        """
        Initialize the VR system manager.
        """
        self.vr_system = None

    def initialize_vr_system(self):
        """
        Initialize the VR system.
        """
        try:
            openvr.init(openvr.VRApplication_Other)
            self.vr_system = openvr.VRSystem()
            print(f"Starting Capture")
        except Exception as e:
            print(f"Failed to initialize VR system: {e}")
            return False
        return True

    def get_tracker_data(self):
        """
        Retrieve tracker data from the VR system.
        """
        poses = self.vr_system.getDeviceToAbsoluteTrackingPose(
            openvr.TrackingUniverseStanding, 0, openvr.k_unMaxTrackedDeviceCount)
        return poses

    def print_discovered_objects(self):
        """
        Print information about discovered VR devices.
        """
        for device_index in range(openvr.k_unMaxTrackedDeviceCount):
            device_class = self.vr_system.getTrackedDeviceClass(device_index)
            if device_class != openvr.TrackedDeviceClass_Invalid:
                serial_number = self.vr_system.getStringTrackedDeviceProperty(
                    device_index, openvr.Prop_SerialNumber_String)
                model_number = self.vr_system.getStringTrackedDeviceProperty(
                    device_index, openvr.Prop_ModelNumber_String)
                print(f"Device {device_index}: {serial_number} ({model_number})")

    def shutdown_vr_system(self):
        """
        Shutdown the VR system.
        """
        if self.vr_system:
            openvr.shutdown()
            
class DataConverter:
    @staticmethod
    def convert_to_quaternion(pose_mat):
        """
        Convert pose matrix to quaternion and position.
        """
        r_w = math.sqrt(abs(1 + pose_mat[0][0] + pose_mat[1][1] + pose_mat[2][2])) / 2
        if r_w == 0: r_w = 0.0001
        r_x = (pose_mat[2][1] - pose_mat[1][2]) / (4 * r_w)
        r_y = (pose_mat[0][2] - pose_mat[2][0]) / (4 * r_w)
        r_z = (pose_mat[1][0] - pose_mat[0][1]) / (4 * r_w)

        x = pose_mat[0][3]
        y = pose_mat[1][3]
        z = pose_mat[2][3]

        return [x, y, z, r_w, r_x, r_y, r_z]
    
    def conver_to_rpy(pose_mat):
        """
        Convert pose matrix to roll, pitch, yaw angles.
        """
        x = pose_mat[0][3]
        y = pose_mat[1][3]
        z = pose_mat[2][3]

        r_x = math.atan2(pose_mat[2][1], pose_mat[2][2])
        r_y = math.atan2(-pose_mat[2][0], math.sqrt(pose_mat[2][1]**2 + pose_mat[2][2]**2))
        r_z = math.atan2(pose_mat[1][0], pose_mat[0][0])

        return [x, y, z, r_x, r_y, r_z]
    
def main():
    vr_manager = VRSystemManager()

    if not vr_manager.initialize_vr_system():
        return
    try:
        while True:
            poses = vr_manager.get_tracker_data()
            for i in range(openvr.k_unMaxTrackedDeviceCount):
                if poses[i].bPoseIsValid:
                    device_class = vr_manager.vr_system.getTrackedDeviceClass(i)
                    if device_class == openvr.TrackedDeviceClass_GenericTracker:
                        current_time = time.time()
                        # position = DataConverter.convert_to_quaternion(poses[i].mDeviceToAbsoluteTracking) # [x, y, z, r_w, r_x, r_y, r_z]
                        position = DataConverter.conver_to_rpy(poses[i].mDeviceToAbsoluteTracking)
                        print(f"Tracker {i - 1}: {position}")
            precise_wait(1 / SAMPLING_RATE)
    except KeyboardInterrupt:
        print("\nStopping data collection...")
    finally:
        vr_manager.shutdown_vr_system()

if __name__== "__main__":
    main()