import os

folder = "plugin_dev_zh"
for filename in os.listdir(folder):
    if filename.endswith(".md"):
        old_path = os.path.join(folder, filename)
        new_filename = filename[:-3] + ".mdx"
        new_path = os.path.join(folder, new_filename)

        # 重命名文件
        os.rename(old_path, new_path)
        print(f"Renamed '{old_path}' to '{new_path}'")