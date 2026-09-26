def compute_metrics(pred, gt):
    """
    计算二值图的各类评估指标：Precision, Recall, F1-score, Accuracy, IoU
    :param pred: 二值预测图 (numpy.ndarray, 0/1)
    :param gt: 二值真值图 (numpy.ndarray, 0/1)
    :return: dict 包含五个指标
    """
    assert pred.shape == gt.shape, "预测图与标签图尺寸不一致"

    pred = pred.astype(bool)
    gt = gt.astype(bool)

    TP = (pred & gt).sum()  # 预测为正，且为真
    FP = (pred & ~gt).sum()  # 预测为正，但为假
    FN = (~pred & gt).sum()  # 预测为负，但为真
    TN = (~pred & ~gt).sum()  # 预测为负，且为假

    precision = TP / (TP + FP + 1e-8)
    recall = TP / (TP + FN + 1e-8)
    f1 = 2 * precision * recall / (precision + recall + 1e-8)
    iou = TP / (TP + FP + FN + 1e-8)
    acc = (TP + TN) / (TP + TN + FP + FN + 1e-8)

    return {
        'Precision': precision,
        'Recall': recall,
        'F1': f1,
        'IoU': iou,
        'Accuracy': acc
    }
