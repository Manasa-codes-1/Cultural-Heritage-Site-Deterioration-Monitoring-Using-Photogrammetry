from data.dataset import readIndex, dataReadPip, loadedDataset
from model.deepcrack import DeepCrack
from trainer import DeepCrackTrainer
import cv2
from tqdm import tqdm
import numpy as np
import torch
import os

os.environ["CUDA_VISIBLE_DEVICES"] = '0'


def compute_metrics(pred, target):
    # 计算 True Positive (TP), False Positive (FP), True Negative (TN), False Negative (FN)
    TP = ((pred == 1) & (target == 1)).sum().item()
    FP = ((pred == 1) & (target == 0)).sum().item()
    TN = ((pred == 0) & (target == 0)).sum().item()
    FN = ((pred == 0) & (target == 1)).sum().item()

    # 计算 Precision, Recall, F1-score 和 Accuracy
    precision = TP / (TP + FP + 1e-6)  # 防止除以0
    recall = TP / (TP + FN + 1e-6)
    f1_score = 2 * precision * recall / (precision + recall + 1e-6)
    accuracy = (TP + TN) / (TP + TN + FP + FN + 1e-6)

    return precision, recall, f1_score, accuracy


def test(test_data_path='data/localtrain/val.txt',
         save_path='data/localtrain/result/',
         pretrained_model='checkpoints/MyDeepCrack/checkpoints/MyDeepCrack_MyDeepCrack_epoch(49)_0000098_2025-05-06-11-36-45.pth', ):

    if not os.path.exists(save_path):
        os.mkdir(save_path)

    test_pipline = dataReadPip(transforms=None)

    test_list = readIndex(test_data_path)

    test_dataset = loadedDataset(test_list, preprocess=test_pipline)

    test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=1,
                                              shuffle=False, num_workers=1, drop_last=False)

    # -------------------- build trainer --------------------- #

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    num_gpu = torch.cuda.device_count() if torch.cuda.is_available() else 1

    model = DeepCrack()

    model = torch.nn.DataParallel(model, device_ids=range(num_gpu))
    model.to(device)

    trainer = DeepCrackTrainer(model).to(device)

    model.load_state_dict(trainer.saver.load(pretrained_model, multi_gpu=True))

    model.eval()

    # Initialize variables to track metrics
    total_precision, total_recall, total_f1, total_accuracy = 0, 0, 0, 0
    num_batches = 0

    with torch.no_grad():
        for names, (img, lab) in tqdm(zip(test_list, test_loader)):
            if torch.cuda.is_available():
                test_data, test_target = img.type(torch.cuda.FloatTensor).to(device), lab.type(torch.cuda.FloatTensor).to(device)
            else:
                test_data, test_target = img.type(torch.FloatTensor).to(device), lab.type(torch.FloatTensor).to(device)
            
            # Get prediction
            test_pred = trainer.val_op(test_data, test_target)
            test_pred = torch.sigmoid(test_pred[0].cpu().squeeze())

            # Save the result images
            save_pred = torch.zeros((512 * 2, 512))
            save_pred[:512, :] = test_pred
            save_pred[512:, :] = lab.cpu().squeeze()
            save_name = os.path.join(save_path, os.path.split(names[1])[1])
            save_pred = save_pred.numpy() * 255
            cv2.imwrite(save_name, save_pred.astype(np.uint8))

            # Compute metrics
            precision, recall, f1_score, accuracy = compute_metrics(test_pred.cpu().numpy(), test_target.cpu().numpy())


            # Accumulate metrics for average calculation
            total_precision += precision
            total_recall += recall
            total_f1 += f1_score
            total_accuracy += accuracy
            num_batches += 1

    # Print average metrics
    print(f"Average Precision: {total_precision / num_batches:.4f}")
    print(f"Average Recall: {total_recall / num_batches:.4f}")
    print(f"Average F1-score: {total_f1 / num_batches:.4f}")
    print(f"Average Accuracy: {total_accuracy / num_batches:.4f}")


if __name__ == '__main__':
    test()




