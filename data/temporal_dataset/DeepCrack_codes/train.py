from data.augmentation import augCompose, RandomBlur, RandomColorJitter
from data.dataset import readIndex, dataReadPip, loadedDataset
from tqdm import tqdm
from model.deepcrack import DeepCrack
from trainer import DeepCrackTrainer
from config import Config as cfg
import numpy as np
import torch
import os
import cv2
import sys
import pandas as pd
from tools.metric import compute_metrics

os.environ["CUDA_VISIBLE_DEVICES"] = str(cfg.gpu_id)


def resize_to_1000x1000(image, label):
    size=512
    image = cv2.resize(image, (size, size), interpolation=cv2.INTER_LINEAR)
    label = cv2.resize(label, (size, size), interpolation=cv2.INTER_NEAREST)
    return image, label


def wrap_resize(dataset):
    class ResizeWrapper(torch.utils.data.Dataset):
        def __init__(self, dataset):
            self.dataset = dataset

        def __len__(self):
            return len(self.dataset)

        def __getitem__(self, idx):
            img, lab = self.dataset[idx]
            img = img.permute(1, 2, 0).numpy() * 255
            lab = lab.numpy()
            img = img.astype(np.uint8)
            lab = (lab * 255).astype(np.uint8)
            img, lab = resize_to_1000x1000(img, lab)
            img = torch.from_numpy(img.transpose(2, 0, 1)).float() / 255.0
            lab = torch.from_numpy(lab).float()
            return img, lab

    return ResizeWrapper(dataset)


def main():
    data_augment_op = augCompose(transforms=[[RandomColorJitter, 0.5], [RandomBlur, 0.2]])
    train_pipline = dataReadPip(transforms=data_augment_op)
    test_pipline = dataReadPip(transforms=None)

    train_dataset = loadedDataset(readIndex(cfg.train_data_path, shuffle=True), preprocess=train_pipline)
    test_dataset = loadedDataset(readIndex(cfg.test_data_path), preprocess=test_pipline)

    train_dataset = wrap_resize(train_dataset)
    test_dataset = wrap_resize(test_dataset)

    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=cfg.train_batch_size,
                                               shuffle=True, num_workers=cfg.num_workers, drop_last=True)

    val_loader = torch.utils.data.DataLoader(test_dataset, batch_size=cfg.val_batch_size,
                                             shuffle=False, num_workers=cfg.num_workers, drop_last=True)

    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

    model = DeepCrack()
    model = torch.nn.DataParallel(model, device_ids=[0])
    model.to(device)

    trainer = DeepCrackTrainer(model).to(device)
    trainer.vis = None  # 禁用 visdom

    if cfg.pretrained_model:
        pretrained_dict = trainer.saver.load(cfg.pretrained_model, multi_gpu=True)
        model_dict = model.state_dict()
        pretrained_dict = {k: v for k, v in pretrained_dict.items() if k in model_dict}
        model_dict.update(pretrained_dict)
        model.load_state_dict(model_dict)

    train_loss_list = []
    val_loss_list = []
    iou_list = []
    f1_list = []
    acc_list = []
    precision_list = []
    recall_list = []

    best_val_loss = float('inf')

    try:
        for epoch in range(1, cfg.epoch + 1):
            model.train()
            bar = tqdm(enumerate(train_loader), total=len(train_loader))
            bar.set_description(f"Epoch {epoch} --- Training")
            for idx, (img, lab) in bar:
                data, target = img.to(device), lab.to(device)
                pred = trainer.train_op(data, target)

            train_loss_list.append(trainer.log_loss['total_loss'])

            if epoch % cfg.val_every_epoch == 0:
                model.eval()
                total_loss, total_iou, total_f1, total_acc, total_precision, total_recall = 0, 0, 0, 0, 0, 0
                count = 0

                with torch.no_grad():
                    for img, lab in val_loader:
                        val_data, val_target = img.to(device), lab.to(device)
                        val_pred = trainer.val_op(val_data, val_target)[0]
                        val_pred = torch.sigmoid(val_pred)
                        loss = trainer.log_loss['total_loss']

                        total_loss += loss
                        for i in range(val_pred.shape[0]):
                            pred_np = (val_pred[i, 0] > 0.5).cpu().numpy().astype(np.uint8)
                            target_np = val_target[i].cpu().numpy().astype(np.uint8)
                            metrics = compute_metrics(pred_np, target_np)
                            total_iou += metrics['IoU']
                            total_f1 += metrics['F1']
                            total_acc += metrics['Accuracy']
                            total_precision += metrics['Precision']
                            total_recall += metrics['Recall']
                        count += val_pred.shape[0]

                val_avg_loss = total_loss / count
                val_loss_list.append(val_avg_loss)
                iou_list.append(total_iou / count)
                f1_list.append(total_f1 / count)
                acc_list.append(total_acc / count)
                precision_list.append(total_precision / count)
                recall_list.append(total_recall / count)

                if val_avg_loss < best_val_loss:
                    best_val_loss = val_avg_loss
                    trainer.saver.save(model, tag='best_model')
            else:
                val_loss_list.append(None)
                iou_list.append(None)
                f1_list.append(None)
                acc_list.append(None)
                precision_list.append(None)
                recall_list.append(None)

        trainer.saver.save(model, tag='final_model')

        df = pd.DataFrame({
            'epoch': list(range(1, len(train_loss_list) + 1)),
            'train_loss': train_loss_list,
            'val_loss': val_loss_list,
            'iou': iou_list,
            'f1': f1_list,
            'acc': acc_list,
            'precision': precision_list,
            'recall': recall_list
        })
        os.makedirs('logs', exist_ok=True)
        df.to_csv('logs/metrics_deepcrack.csv', index=False)
        print("✅ Saved CSV log to logs/metrics_deepcrack.csv")

    except KeyboardInterrupt:
        trainer.saver.save(model, tag='Auto_Save_Model')
        print('\n⛔️ Interrupted. Saved model.')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)


if __name__ == '__main__':
    main()
