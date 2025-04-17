import os
import re

def fix_link(match):
    link_text = match.group(1)
    link_target = match.group(2)
    # 检查链接是否以 /plugin_dev_zh/ 开头且不以 .zh 结尾
    if link_target.startswith('/plugin_dev_zh/') and not link_target.endswith('.zh'):
        # 检查是否已经是 .mdx 文件链接，避免添加 .zh.mdx
        if link_target.endswith('.mdx'):
             # 插入 .zh 在 .mdx 之前
             new_target = link_target[:-4] + '.zh.mdx'
        else:
            # 否则直接添加 .zh
            new_target = link_target + '.zh'
        print(f"  Updating link: {link_target} -> {new_target}")
        return f'[{link_text}]({new_target})'
    # 如果链接不需要修改，则原样返回
    return match.group(0)

folder = "plugin_dev_zh"
# 正则表达式查找 Markdown 链接 [text](/plugin_dev_zh/...)
# 它会捕获链接文本 (group 1) 和链接目标 (group 2)
link_pattern = re.compile(r'\[([^\]]+)\]\((/plugin_dev_zh/[^\)\s]+)\)')

print(f"Processing files in folder: {folder}")

for filename in os.listdir(folder):
    if filename.endswith(".mdx"):
        filepath = os.path.join(folder, filename)
        print(f"Processing file: {filepath}")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # 使用 re.sub 和回调函数来替换链接
            new_content = link_pattern.sub(fix_link, content)

            # 只有当内容发生变化时才写回文件
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"  File updated: {filepath}")
            else:
                print(f"  No changes needed for: {filepath}")
        except Exception as e:
            print(f"Error processing file {filepath}: {e}")

print("Finished processing all .mdx files.")
