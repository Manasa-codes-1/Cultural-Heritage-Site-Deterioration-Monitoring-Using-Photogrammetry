import os
import sys
from pathlib import Path
import torch
import numpy as np
from PIL import Image

# Add path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "data" / "temporal_dataset" / "DeepCrack_codes"))

from model.deepcrack import DeepCrack

def test_load():
    ckpt_path = root_dir / "data" / "temporal_dataset" / "DeepCrack_codes" / "checkpoints" / "MyDeepCrack_final.pth"
    print(f"Loading checkpoint from: {ckpt_path}")
    assert ckpt_path.exists(), f"Checkpoint does not exist: {ckpt_path}"
    
    device = torch.device("cpu")
    model = DeepCrack().to(device)
    
    state = torch.load(str(ckpt_path), map_location=device, weights_only=False)
    if isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]

    new_state = {}
    for k, v in state.items():
        if k.startswith("module."):
            new_state[k[len("module."):]] = v
        else:
            new_state[k] = v
            
    model.load_state_dict(new_state, strict=True)
    model.eval()
    print("SUCCESS: Model weights loaded successfully!")
    
    # Test on a real validation image
    val_img_path = root_dir / "data" / "temporal_dataset" / "DeepCrack_codes" / "dataset" / "val" / "images" / "111212-1.jpg"
    assert val_img_path.exists(), f"Val image not found: {val_img_path}"
    
    img = Image.open(val_img_path).convert("RGB")
    orig_w, orig_h = img.size
    print(f"Loaded validation image: {val_img_path.name}, size: {orig_w}x{orig_h}")
    
    # Preprocess
    img_resized = img.resize((512, 512), Image.BILINEAR)
    img_np = np.array(img_resized, dtype=np.float32) / 255.0
    # normalize mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225] or standard
    img_tensor = torch.from_numpy(img_np.transpose((2, 0, 1))).unsqueeze(0).to(device)
    
    with torch.no_grad():
        outputs = model(img_tensor)
        pred_logits = outputs[0]  # (1, 1, 512, 512)
        prob = torch.sigmoid(pred_logits)[0, 0].cpu().numpy()
        
    print(f"Prediction output shape: {prob.shape}, min: {prob.min():.4f}, max: {prob.max():.4f}, mean: {prob.mean():.4f}")
    crack_pixels = (prob > 0.5).sum()
    print(f"Crack pixels detected at threshold 0.5: {crack_pixels} ({crack_pixels / (512*512) * 100:.2f}%)")

if __name__ == "__main__":
    test_load()
