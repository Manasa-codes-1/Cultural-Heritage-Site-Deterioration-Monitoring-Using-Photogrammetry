import PIL.Image
import PIL.ImageOps
import os

def compress_images(image_path, target_resolution: tuple):
    """
    Compresses an image to a target resolution.

    :param image_path: The path to the image to compress.
    :param target_resolution: The target resolution to compress to.
    :return: The compressed image.
    """
    image = PIL.Image.open(image_path)
    image = image.resize(target_resolution)
    return image

if __name__ == '__main__':
    image_dir = input()
    target_resolution = (512, 512)
    # traverse the directory
    for root, dirs, files in os.walk(image_dir):
        for file in files:
            if file.endswith(".jpg") or file.endswith(".png") or file.endswith(".bmp"):
                image_path = os.path.join(root, file)
                compressed_image = compress_images(image_path, target_resolution)
                compressed_image.save(image_path)
