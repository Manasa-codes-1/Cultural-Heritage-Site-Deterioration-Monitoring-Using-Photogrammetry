import os

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

    origin_dir = os.path.join(directory, "origin")
    gt_dir = os.path.join(directory, "gt")

    origin_files = list_files_in_directory(origin_dir); origin_files.sort()
    gt_files = list_files_in_directory(gt_dir); gt_files.sort()

    i = j = 0

    while i < len(origin_files) and j < len(gt_files):
        origin_filename = os.path.basename(origin_files[i])
        origin_extension = os.path.splitext(origin_filename)[1]
        origin_filename = os.path.splitext(origin_filename)[0]
        gt_filename = os.path.basename(gt_files[j])
        gt_extension = os.path.splitext(gt_filename)[1]
        gt_filename = os.path.splitext(gt_filename)[0]
        if origin_filename == gt_filename:
            i += 1
            j += 1
        else:
            if origin_filename < gt_filename:
                os.remove(origin_files[i])
                i += 1
            else:
                os.remove(gt_files[j])
                j += 1

    while i < len(origin_files):
        os.remove(origin_files[i])
        i += 1

    while j < len(gt_files):
        os.remove(gt_files[j])
        j += 1

    print("Done!")
