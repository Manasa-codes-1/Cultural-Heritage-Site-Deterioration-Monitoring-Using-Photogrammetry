from data.dataset import readIndex, dataReadPip, loadedDataset
from model.deepcrack import DeepCrack
import cv2
import torch
import tqdm
import numpy as np

import os

# input_path = "inputs/2023.11"
# output_path = "outputs/2023.11"
# if not os.path.exists(output_path):
#     os.makedirs(output_path, exist_ok=True)
input_path='test'
output_path='test.png'



model = DeepCrack()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#model = torch.nn.DataParallel(model, device_ids=[0])
model.to(device)

model.load_state_dict(torch.load("checkpoints/MyDeepCrack2/checkpoints/MyDeepCrack2_MyDeepCrack2_epoch(149)_0000232_2025-07-15-18-05-54.pth", map_location=None if torch.cuda.is_available() else 'cpu'))

input_list = []
for root, dirs, files in os.walk(input_path):
    for file in files:
        input_list.append(os.path.join(root, file))

print(f"Found {len(input_list)} files in {input_path}")

# set the model to evaluation mode
model.eval()

with torch.no_grad():
    for input_file in tqdm.tqdm(input_list):
        # read the image and preprocess it
        img = cv2.imread(input_file, cv2.IMREAD_COLOR)
        size = img.shape[:2]
        img = cv2.resize(img, (1440, 1440))
        img = img.transpose((2, 0, 1))
        img = np.expand_dims(img, axis=0)
        img = img / 255.0
        img = torch.from_numpy(img).float()

        # make the prediction
        output = model(img.to(device))
        output = torch.sigmoid(output[0].cpu().squeeze())
        output[output > 0.5] = 1
        output[output <= 0.5] = 0
        save_pred = output
        save_name = os.path.join(output_path, os.path.split(input_file)[1])
        save_pred = save_pred.numpy() * 255

        # resize the output to the original size
        save_pred = cv2.resize(save_pred, (size[1], size[0]))
        cv2.imwrite(save_name, save_pred)
