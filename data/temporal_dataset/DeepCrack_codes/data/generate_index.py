import os
import random

def list_files_in_directory(directory):
    try:
        # 获取指定目录中的所有文件和目录
        entries = os.listdir(directory)
        # 过滤出文件，并将文件路径转换为绝对路径
        file_paths = [os.path.abspath(os.path.join(directory, entry)) for entry in entries if os.path.isfile(os.path.join(directory, entry))]
        return file_paths
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

if __name__ == '__main__':
    directory = input()

    # 9 for training, 1 for validation
    ratio = 9 / 1

    dirs = ["origin", "mask", "gt"]
    origin_dir = os.path.join(directory, dirs[0])
    gt_dir = os.path.join(directory, dirs[2])

    origin_files = list_files_in_directory(origin_dir); origin_files.sort()
    gt_files = list_files_in_directory(gt_dir); gt_files.sort()

    indexes = list(range(len(origin_files)))
    random.shuffle(indexes)

    with open("train.txt", "w") as file:
        for i in range(int(len(indexes) * ratio / (ratio + 1))):
            file.write(f"{origin_files[indexes[i]]} {gt_files[indexes[i]]}\n")
    with open("val.txt", "w") as file:
        for i in range(int(len(indexes) * ratio / (ratio + 1)), len(indexes)):
            file.write(f"{origin_files[indexes[i]]} {gt_files[indexes[i]]}\n")