import cv2
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from skimage.morphology import skeletonize

def load_and_preprocess(path):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
    skeleton = skeletonize(binary > 0)
    return binary, skeleton

def local_quadratic_fit(x_vals, y_vals, window_size=10):
    fits = []
    for i in range(0, len(x_vals) - window_size, window_size):
        # Extract points within the window
        x_window = x_vals[i:i + window_size]
        y_window = y_vals[i:i + window_size]
        
        # Perform quadratic fitting on the window
        fit_params = np.polyfit(x_window, y_window, 2)
        fit_func = np.poly1d(fit_params)
        
        # Store the fitted function and the x values for the window
        fits.append((fit_func, x_window))
        
    return fits

def plot_local_fits(x_vals, y_vals, fits):
    plt.scatter(x_vals, y_vals, label='Data points', color='green')
    
    for fit_func, x_window in fits:
        plt.plot(x_window, fit_func(x_window), label='Fitted quadratic', color='red', linewidth=2)
    
    plt.xlabel("X (pixels)")
    plt.ylabel("Y (pixels)")
    plt.legend()
    plt.show()

def fit_quadratic_from_skeleton(skeleton):
    points = np.argwhere(skeleton)
    x_vals = points[:, 1]
    y_vals = points[:, 0]
    
    # Perform local quadratic fitting
    fits = local_quadratic_fit(x_vals, y_vals, window_size=10)
    
    return fits, points

def measure_width_from_skeleton(binary, skeleton, scale=1.0, sample_stride=5):
    fits, skeleton_points = fit_quadratic_from_skeleton(skeleton)
    results = []

    for pt in skeleton_points[::sample_stride]:
        y0, x0 = pt
        # Here, we select the local fit for the given point
        fit_func, x_window = fits[0]  # Take the first fit function as an example
        dy_dx = np.polyder(fit_func)(x0)
        k_normal = -1 / dy_dx if dy_dx != 0 else 0
        pt_left = find_edge_point_along_normal(binary, x0, y0, k_normal, -1)
        pt_right = find_edge_point_along_normal(binary, x0, y0, k_normal, 1)

        if pt_left and pt_right:
            width_px = np.linalg.norm(np.array(pt_left) - np.array([x0, y0])) + \
                       np.linalg.norm(np.array(pt_right) - np.array([x0, y0]))
            width_mm = width_px * scale
            results.append({
                "center_x": x0,
                "center_y": y0,
                "left_x": pt_left[0],
                "left_y": pt_left[1],
                "right_x": pt_right[0],
                "right_y": pt_right[1],
                "width_px": round(width_px, 2),
                "width_mm": round(width_mm, 3)
            })

    return fits, skeleton_points, results

def find_edge_point_along_normal(binary, x0, y0, k_normal, direction, max_range=100):
    h, w = binary.shape
    for i in range(1, max_range):
        dx = direction * i / np.sqrt(1 + k_normal ** 2)
        dy = k_normal * dx
        xt = int(x0 + dx)
        yt = int(y0 + dy)
        if xt < 0 or yt < 0 or xt >= w or yt >= h:
            break
        if binary[yt, xt] == 0:
            return (xt, yt)
    return None

def visualize_skeleton_and_width(binary, skeleton, skeleton_points, results, save_path="fig2_skeleton_width.svg"):

    img_rgb1 = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)  # 骨架图
    img_rgb2 = img_rgb1.copy()                          # 测宽图

    for y, x in skeleton_points:
        cv2.circle(img_rgb1, (x, y), 1, (0, 255, 0), -1)

    for row in results:
        pt_left = (int(row['left_x']), int(row['left_y']))
        pt_right = (int(row['right_x']), int(row['right_y']))
        cv2.line(img_rgb2, pt_left, pt_right, (0, 0, 255), 1)
        cv2.circle(img_rgb2, (int(row['center_x']), int(row['center_y'])), 1, (0, 255, 0), -1)

    crop_size = 400
    height=300
    width=300
    h, w = binary.shape
    cx, cy = w // 2, h // 2
    fix=70
    x_min = max(cx - width // 2, 0)-50
    x_max = min(cx + width // 2, w)-50
    y_min = max(cy - height // 2, 0)-120
    y_max = min(cy + height // 2, h)-120

    img_rgb1_crop = img_rgb1[y_min:y_max, x_min:x_max]
    img_rgb2_crop = img_rgb2[y_min:y_max, x_min:x_max]

    plt.rcParams['font.family'] = 'Times New Roman'
    fig, axes = plt.subplots(1, 2, figsize=(7, 3.5),dpi=500)

    axes[0].imshow(cv2.cvtColor(img_rgb1_crop, cv2.COLOR_BGR2RGB))
    axes[0].set_xlabel("X (pixels)")
    axes[0].set_ylabel("Y (pixels)")
    axes[0].axis("on")
    axes[0].text(305, 300, '(a)', fontsize=10, color='black', fontname='Times New Roman')

    axes[1].imshow(cv2.cvtColor(img_rgb2_crop, cv2.COLOR_BGR2RGB))
    axes[1].set_xlabel("X (pixels)")
    axes[1].set_ylabel("Y (pixels)")
    axes[1].axis("on")
    axes[1].text(305, 300, '(b)', fontsize=10, color='black', fontname='Times New Roman')
    
    plt.tight_layout()
    plt.savefig(save_path, format='svg', bbox_inches='tight')
    plt.close()

image_path = 'outputs/2023.11/clean_q2-3.bmp'
binary, skeleton = load_and_preprocess(image_path)

fits, skeleton_points, results = measure_width_from_skeleton(binary, skeleton, scale=0.1608)

visualize_skeleton_and_width(binary, skeleton, skeleton_points, results, save_path="fig7.svg")

# 输出测量数据
pd.DataFrame(results).to_excel("width.xlsx", index=False)
