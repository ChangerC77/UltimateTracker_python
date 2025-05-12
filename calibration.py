import pandas as pd
import numpy as np
try:
    import open3d as o3d
except:
    o3d = None
from functools import reduce
from sklearn.decomposition import PCA
from scipy.spatial.transform import Rotation


def read_poses_from_csv(csv_path):
    """Read pose data from CSV file"""
    df = pd.read_csv(csv_path)
    print(f"Original data has {len(df)} rows")
    return df

def create_coordinate_frame(size=1.0):
    """Create Open3D coordinate frame mesh"""
    return o3d.geometry.TriangleMesh.create_coordinate_frame(size=size)

def write_pc(points, dst, colors=None):
    """Write point cloud to file"""
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    if colors is not None:
        pcd.colors = o3d.utility.Vector3dVector(colors)
    o3d.io.write_point_cloud(dst, pcd)

def get_pose(row):
    """Convert row data to 4x4 transformation matrix"""
    transform = np.eye(4)
    
    # Handle rotation (quaternion)
    quat = np.array([row['RotationX'], row['RotationY'], row['RotationZ'], row['RotationW']])
    R = Rotation.from_quat([quat[0], quat[1], quat[2], quat[3]]).as_matrix()  # scipy uses x,y,z,w order
    transform[:3, :3] = R
    
    # Set position
    transform[:3, 3] = np.array([row['PositionX'], row['PositionY'], row['PositionZ']])
    return transform

def get_pose_from_df(df):
    """Get poses from dataframe"""
    poses = []
    for _, row in df.iterrows():
        poses.append(get_pose(row))
    return np.array(poses)

def visualize_poses(poses, transform=None):
    """Visualize poses using Open3D"""
    frames = []
    positions = []
    
    for i, pose in enumerate(poses):
        if transform is not None:
            pose = transform @ pose
        positions.append(pose[:3,3])
 
        if i % 10 == 0:
            frame = create_coordinate_frame(size=0.1)
            frame.transform(pose)
            frames.append(frame)
    
    o3d.io.write_triangle_mesh(f"poses_{len(frames)}.ply", reduce(lambda x,y: x+y, frames))
    positions = np.array(positions)
    write_pc(positions, f"poses_pc_{len(positions)}.ply")

def get_pcd_vec(pts):
    """Get principal direction vector from points"""
    pts_centered = pts - pts.mean(axis=0)
    pca = PCA(n_components=1)
    pca.fit(pts_centered)
    return pca.components_[0]

def orthogonalize(v1, v2):
    """Make v2 orthogonal to v1"""
    projection = np.dot(v2, v1) * v1
    ortho = v2 - projection
    return ortho / np.linalg.norm(ortho)

def get_transform_PCA(pose_0, poses_x, poses_z):
    """Calibrate poses using reference pose and x/z trajectories"""
    # Get points from poses
    pts_x = poses_x[...,:3,3]
    pts_z = poses_z[...,:3,3]
    
    # Get principal vectors
    vec_x = get_pcd_vec(pts_x.copy())
    vec_z = get_pcd_vec(pts_z.copy())
    vec_x = vec_x / np.linalg.norm(vec_x)
    vec_z = orthogonalize(vec_x, vec_z)
    vec_y = np.cross(vec_z, vec_x)

    origin = pose_0[:3,3]

    # Check and fix vector directions
    dir_x = (pts_x-origin)@vec_x
    idx = np.argmax(np.abs(dir_x))
    max_dir_x = dir_x[idx]
    if max_dir_x < 0:
        print('invert x')
        vec_x = -vec_x
        
    dir_z = (pts_z-origin)@vec_z
    idx = np.argmax(np.abs(dir_z))
    max_dir_z = dir_z[idx]
    if max_dir_z < 0:
        print('invert z')
        vec_z = -vec_z
    print(max_dir_x, max_dir_z)

    # Create rotation matrix
    rot_matrix = np.eye(3)
    rot_matrix[:3,0] = vec_x
    rot_matrix[:3,1] = vec_y
    rot_matrix[:3,2] = vec_z

    transform = np.eye(4)
    transform[:3,:3] = rot_matrix
        
    return transform

def apply_transform(poses_all, transform,pose_0):
    flag=False
    if poses_all.ndim==2:
        poses_all=poses_all[None,...]
        flag=True

    ## PCA only on translation
    poses_all[:,:3,3] = (poses_all[:,:3,3]-pose_0[:3,3])@np.linalg.inv(transform[:3,:3]).T
    ## rotation relative to pose_0
    poses_all[:,:3,:3] = np.linalg.inv(pose_0[:3,:3])@poses_all[:,:3,:3]
    if flag:
        poses_all=poses_all[0,...]
    return poses_all

def load_calibration():
    data = np.load("calibration.npz")
    return data["pose_0"],data["transform"]

def main(vis=False):
    csv_path = "/home/bj-01/vive_tracker_pose/tracker_data_X.csv"
    poses_x = get_pose_from_df(read_poses_from_csv(csv_path))
    csv_path = "/home/bj-01/vive_tracker_pose/tracker_data_Z.csv"
    poses_z = get_pose_from_df(read_poses_from_csv(csv_path))
    pose_0 = poses_x[0]
    poses_all = np.concatenate([poses_x, poses_z], axis=0)
    transform_PCA = get_transform_PCA(pose_0, poses_x, poses_z)
    np.savez("calibration.npz",pose_0=pose_0,transform=transform_PCA)
    pose_0,transform_PCA = load_calibration()

    poses_all = apply_transform(poses_all, transform_PCA,pose_0)
    if vis and o3d is not None:
        # Visualize coordinate frame
        frame = create_coordinate_frame(size=0.1)
        frame.transform(transform_PCA)
        o3d.io.write_triangle_mesh("poses_origin.ply", frame)
        visualize_poses(poses_all)

if __name__ == "__main__":
    main(vis=True)