import cv2
import numpy as np

img = cv2.imread("test/2_6_2_1234.jpeg", cv2.IMREAD_GRAYSCALE)

# 1. 识别近似黑色区域（拼接空白）
_, mask_black = cv2.threshold(img, 5, 255, cv2.THRESH_BINARY_INV)

# mask_black == 255 的地方是黑色 blank area

# 2. 将黑色区域替换为白色（或中灰 200）
img_filled = img.copy()
img_filled[mask_black == 255] = 255   # 或 200

cv2.imwrite("stitched_filled.png", img_filled)
