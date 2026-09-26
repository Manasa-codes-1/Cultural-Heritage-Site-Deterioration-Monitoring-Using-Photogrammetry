import cv2
import numpy as np
import matplotlib.pyplot as plt
from skimage.morphology import skeletonize
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Times New Roman']
plt.rcParams['axes.unicode_minus'] = False

def extract_skeleton_coords(image_path, scale=1.0):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
    skeleton = skeletonize(binary > 0)
    skeleton_points = np.argwhere(skeleton)  # (y, x)
    skeleton_points = np.array([[x * scale, y * scale] for y, x in skeleton_points])
    skeleton_points = skeleton_points[np.argsort(skeleton_points[:, 0])]
    return skeleton_points

def flatten_vector(coords):
    return coords.flatten()

def cosine_similarity(v1, v2):
    if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
        return -1
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def visualize_matching_stop_early(base_coords, target_coords, window_size=400, delay=0.05, stop_threshold=0.98,stop_max_threshold=0.989):
    index=0
    base_vec = flatten_vector(base_coords[index:window_size+index])

    fig, ax = plt.subplots(figsize=(10, 6))

    for i in range(len(target_coords) - window_size + 1):
        window = target_coords[i:i+window_size]
        target_vec = flatten_vector(window)
        sim = cosine_similarity(base_vec, target_vec)

        ax.clear()
        ax.plot(target_coords[:, 0], target_coords[:, 1], '.', color='lightgray', markersize=2, label="Target graph skeleton")
        ax.plot(window[:, 0], window[:, 1], 'g.-', label=f"Current window (start={i})")
        ax.plot(base_coords[index:window_size+index][:, 0], base_coords[index:window_size+index][:, 1], 'r.-', label="Reference graph segment")

        ax.set_title(f"In sliding: start={i}, cos={sim:.3f}")
        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Y (mm)")
        ax.invert_yaxis()
        ax.legend()
        ax.grid(True)
        plt.pause(delay)

        if sim >= stop_threshold and sim <= stop_max_threshold:
            #fig, ax = plt.subplots(figsize=(7, 7),dpi=300)
            ax.clear()
            ax.plot(target_coords[:, 0], target_coords[:, 1], '.', color='lightgray', markersize=2, label="Target graph skeleton")
            ax.plot(window[:, 0], window[:, 1], 'b.-', label=f" matching section (start={i})")
            ax.plot(base_coords[index:window_size+index][:, 0], base_coords[index:window_size+index][:, 1], 'r.-', label="Reference graph segment")

            ax.set_title(f"Matching successful cos={sim:.4f}",fontsize=11)
            ax.set_xlabel("X (mm)",fontsize=11)
            ax.set_ylabel("Y (mm)",fontsize=11)
            ax.invert_yaxis()
            ax.legend(fontsize=11)
            ax.grid(True)
            plt.show()
            print(f"\n match start：{i}，cos：{sim:.4f}")
            return

    print("not match")

image_info = [
        ("2023.11", "outputs2/2023.11/clean_d2-2-2_Undistorted.bmp", 0.2116),
        ("2024.3", "outputs2/2024.3/clean_d2-2-2_Undistorted.bmp", 0.1829),
        ("2024.7", "outputs2/2024.7/clean_D2-2-2-2_Undistorted.bmp", 0.1610),
        ("2025.1", "outputs2/2025.1/clean_d2-2-2-2_Undistorted.bmp", 0.1866 ),
    ]
base_path = 'outputs2/2024.3/clean_d2-2-2_Undistorted.bmp'
target_path = 'outputs2/2025.1/clean_d2-2-2-2_Undistorted.bmp'
base_scale = 0.1829
target_scale = 0.1866

base_coords = extract_skeleton_coords(base_path, scale=base_scale)
target_coords = extract_skeleton_coords(target_path, scale=target_scale)
print(base_coords[:100,:100],target_coords[:100,:100])
v1 = flatten_vector(base_coords[:100])
v2 = flatten_vector(target_coords[70:170])
sim = cosine_similarity(v1, v2)
print(sim)

visualize_matching_stop_early(
    base_coords,
    target_coords,
    window_size=800,
    delay=0.05,
    stop_threshold=0.9888,stop_max_threshold=0.989
)


