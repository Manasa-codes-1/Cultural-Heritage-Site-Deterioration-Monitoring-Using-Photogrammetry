import os

def generate_txt(image_root, mask_root, output_txt):
    image_files = sorted([f for f in os.listdir(image_root) if f.endswith(('.jpg', '.png', '.bmp'))])
    with open(output_txt, 'w') as f:
        for img in image_files:
            name = os.path.splitext(img)[0]
            img_path = os.path.abspath(os.path.join(image_root, img)).replace('\\', '/')
            mask_path = os.path.abspath(os.path.join(mask_root, name + '.png')).replace('\\', '/')
            if os.path.exists(mask_path):
                f.write(f"{img_path} {mask_path}\n")

if __name__ == '__main__':
    base_dir = 'dataset'
    output_dir = 'data/path_local_txt'
    os.makedirs(output_dir, exist_ok=True)

    generate_txt(
        image_root=os.path.join(base_dir, 'train/images'),
        mask_root=os.path.join(base_dir, 'train/masks'),
        output_txt=os.path.join(output_dir, 'train.txt')
    )

    generate_txt(
        image_root=os.path.join(base_dir, 'val/images'),
        mask_root=os.path.join(base_dir, 'val/masks'),
        output_txt=os.path.join(output_dir, 'val.txt')
    )
