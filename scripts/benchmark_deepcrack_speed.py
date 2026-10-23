import time
import sys
from pathlib import Path
import torch
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path("data/temporal_dataset/DeepCrack_codes").resolve()))
from model.deepcrack import DeepCrack

def benchmark():
    torch.set_num_threads(4)
    model = DeepCrack()
    ckpt_path = Path("data/temporal_dataset/DeepCrack_codes/checkpoints/MyDeepCrack_final.pth")
    state = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    if isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]
    new_state = {(k[7:] if k.startswith("module.") else k): v for k, v in state.items()}
    model.load_state_dict(new_state)
    model.eval()

    val_dir = Path("data/temporal_dataset/DeepCrack_codes/dataset/val/images")
    imgs = sorted(list(val_dir.glob("*.jpg")))[:5]
    print(f"Benchmarking 5 validation images on CPU...", flush=True)
    t0 = time.time()
    with torch.inference_mode():
        for i, img_p in enumerate(imgs):
            im = Image.open(img_p).convert("RGB").resize((512, 512))
            arr = np.array(im, dtype=np.float32).transpose((2, 0, 1)) / 255.0
            inp = torch.from_numpy(arr).unsqueeze(0)
            _ = model(inp)[0]
            print(f"  Image {i+1} done in {time.time()-t0:.2f}s", flush=True)
    t1 = time.time()
    print(f"Total: {t1-t0:.2f}s (Avg: {(t1-t0)/5:.2f}s/img)", flush=True)

if __name__ == "__main__":
    benchmark()
