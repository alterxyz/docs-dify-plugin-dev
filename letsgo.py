import json
import os
import re
from collections import defaultdict

# instruction: 如果进行了大更新，需要重新部署，手动删除实现： `"navigation": {"languages": [{"language": "zh","tabs": [空]`
# --- 配置 ---
DOCS_JSON_PATH = 'docs.json'
DOCS_DIR = 'plugin_dev_zh'
LANGUAGE_CODE = 'zh'
FILE_EXTENSION = '.zh.mdx'
# 更新正则表达式以匹配 '0000-Title.zh.mdx' 格式
FILENAME_PATTERN = re.compile(r'^(\d{4})-(.*?)\.zh\.mdx$')

# --- PWX 到 Group 名称的映射 (新的两 Tab 结构) ---
# (P, W, X) -> (tab_name, group_name, nested_group_name)
PWX_TO_GROUP_MAP = {
    # Tab: 插件开发 (合并了原 P=0 和 P=9, 移除了 013x, 041x)
    #   Group: 概念与入门
    ('0', '1', '1'): ("插件开发", "概念与入门", "概览"),                  # <-- 保留在主流程开头
    #   Group: 开发实践
    ('0', '2', '1'): ("插件开发", "开发实践", "快速开始"),
    ('0', '2', '2'): ("插件开发", "开发实践", "开发 Dify 插件"),
    #   Group: 贡献与发布
    ('0', '3', '1'): ("插件开发", "贡献与发布", "行为准则与规范"),
    ('0', '3', '2'): ("插件开发", "贡献与发布", "发布与上架"),
    ('0', '3', '3'): ("插件开发", "贡献与发布", "常见问题解答"),
    #   Group: 实践案例与示例 (原 043x)
    ('0', '4', '3'): ("插件开发", "实践案例与示例", "开发示例"),          # <-- 保留在主流程
    #   Group: 高级开发 (原 P=9 内容)
    ('9', '2', '2'): ("插件开发", "高级开发", "Extension 与 Agent"),    # <-- P=9 内容整合进来
    ('9', '2', '3'): ("插件开发", "高级开发", "Extension 与 Agent"),    # <-- P=9 内容整合进来
    ('9', '4', '3'): ("插件开发", "高级开发", "Extension 与 Agent"),    # <-- P=9 内容整合进来
    ('9', '2', '4'): ("插件开发", "高级开发", "反向调用"),         # <-- P=9 内容整合进来

    # Tab: 速查与规范 (新的 Tab, 包含原 013x, 041x)
    #   Group: 核心概念与速查 (原 013x)
    ('0', '1', '3'): ("速查与规范", "核心概念与速查", None),             # <-- 移动到新 Tab, 无嵌套组
    #   Group: 核心规范与功能 (原 041x)
    ('0', '4', '1'): ("速查与规范", "核心规范与功能", None),             # <-- 移动到新 Tab, 无嵌套组
    # 注意：如果 013x 或 041x 下的文件很多，也可以给它们加上 Nested Group，
    # 例如 ('0', '1', '3'): ("速查与规范", "快速查阅", "核心概念"),
    # ('0', '4', '1'): ("速查与规范", "技术规范", "核心功能")
    # 这里暂时将它们直接放在 Group 下 (nested_group_name=None)
}


# --- 辅助函数 (与之前版本相同) ---
# ... (get_page_path, extract_existing_pages, _recursive_extract,
#      remove_obsolete_pages, find_or_create_target_group 函数保持不变) ...

# <--- 将之前的辅助函数代码粘贴到这里 --->
def get_page_path(filename):
    """从 mdx 文件名获取 mintlify 页面路径 (去掉 .mdx 后缀)"""
    return os.path.join(DOCS_DIR, filename[:-len('.mdx')])


def extract_existing_pages(navigation_data, lang_code):
    """递归提取指定语言下所有已存在的页面路径"""
    existing_pages = set()
    lang_found = False
    if not navigation_data or 'languages' not in navigation_data:
        print("警告: 'navigation.languages' 未找到")
        return existing_pages, None

    target_lang_nav = None
    for lang_nav in navigation_data.get('languages', []):
        if lang_nav.get('language') == lang_code:
            target_lang_nav = lang_nav
            lang_found = True
            break

    if not lang_found:
        print(f"警告: 语言 '{lang_code}' 在 docs.json 中未找到")
        return existing_pages, None

    for tab in target_lang_nav.get('tabs', []):
        # Handle case where tab might be None or not a dict
        if isinstance(tab, dict):
            for group in tab.get('groups', []):
                # Handle case where group might be None or not a dict
                if isinstance(group, dict):
                    _recursive_extract(group, existing_pages)

    return existing_pages, target_lang_nav


def _recursive_extract(group_item, pages_set):
    """递归辅助函数"""
    # Ensure group_item is a dictionary before proceeding
    if not isinstance(group_item, dict):
        return

    if 'pages' in group_item and isinstance(group_item['pages'], list):
        for page in group_item['pages']:
            if isinstance(page, str):
                pages_set.add(page)
            elif isinstance(page, dict) and 'group' in page:
                # Recurse into nested groups
                _recursive_extract(page, pages_set)


def remove_obsolete_pages(navigation_data, pages_to_remove):
    """递归移除失效的页面条目 (保持与之前版本相同, 稍微健壮一些)"""
    if isinstance(navigation_data, dict):
        if 'pages' in navigation_data and isinstance(navigation_data['pages'], list):
            new_pages = []
            for page in navigation_data['pages']:
                if isinstance(page, str):
                    if page not in pages_to_remove:
                        new_pages.append(page)
                elif isinstance(page, dict):
                    # Recurse into nested group
                    remove_obsolete_pages(page, pages_to_remove)
                    # Keep nested group only if it has pages after cleaning, or maybe always keep structure?
                    # Let's keep structure for now unless explicitly empty dict {} results
                    # Keep if page dict is not empty and has pages
                    if page and page.get('pages'):
                        new_pages.append(page)
                    elif page and 'group' in page and not page.get('pages'):
                        print(f"信息: 嵌套组 '{page.get('group')}' 清理后为空，已保留结构。")
                        # Keep empty nested group structure
                        new_pages.append(page)
                else:
                    new_pages.append(page)  # Keep other types
            navigation_data['pages'] = new_pages

        # Recurse into other dictionary values
        for key, value in navigation_data.items():
            if key != 'pages' and isinstance(value, (dict, list)):
                remove_obsolete_pages(value, pages_to_remove)

    elif isinstance(navigation_data, list):
        i = 0
        while i < len(navigation_data):
            item = navigation_data[i]
            if isinstance(item, str) and item in pages_to_remove:
                navigation_data.pop(i)
            elif isinstance(item, dict):
                remove_obsolete_pages(item, pages_to_remove)
                # Optional: Remove empty top-level groups?
                if 'group' in item and not item.get('pages'):
                    print(f"信息: 顶层组 '{item.get('group')}' 清理后为空，已保留结构。")
                    # navigation_data.pop(i) # Uncomment to remove empty top-level groups
                    # continue # Skip increment if item is removed
                i += 1
            elif isinstance(item, list):  # Recurse into nested lists if any
                remove_obsolete_pages(item, pages_to_remove)
                i += 1
            else:
                i += 1


def find_or_create_target_group(target_lang_nav, tab_name, group_name, nested_group_name):
    """查找或创建目标 Tab 和 Group 结构，返回最低层级的 pages 列表引用 (健壮性稍作提升)"""
    target_tab = None
    # Ensure 'tabs' exists and is a list
    if 'tabs' not in target_lang_nav or not isinstance(target_lang_nav['tabs'], list):
        target_lang_nav['tabs'] = []

    for tab in target_lang_nav['tabs']:
        if isinstance(tab, dict) and tab.get('tab') == tab_name:
            target_tab = tab
            break
    if target_tab is None:
        target_tab = {'tab': tab_name, 'groups': []}
        target_lang_nav['tabs'].append(target_tab)

    target_group = None
    # Ensure 'groups' exists and is a list
    if 'groups' not in target_tab or not isinstance(target_tab['groups'], list):
        target_tab['groups'] = []

    for group in target_tab['groups']:
        if isinstance(group, dict) and group.get('group') == group_name:
            target_group = group
            break
    if target_group is None:
        target_group = {'group': group_name, 'pages': []}
        target_tab['groups'].append(target_group)

    # Ensure 'pages' exists in the target_group and is a list
    if 'pages' not in target_group or not isinstance(target_group['pages'], list):
        target_group['pages'] = []

    # Default container is the top-level group's pages list
    target_pages_container = target_group['pages']

    if nested_group_name:
        target_nested_group = None
        # Find existing nested group
        for item in target_group['pages']:
            if isinstance(item, dict) and item.get('group') == nested_group_name:
                target_nested_group = item
                # Ensure pages list exists in nested group
                target_pages_container = target_nested_group.setdefault(
                    'pages', [])
                # Ensure it's actually a list after setdefault
                if not isinstance(target_pages_container, list):
                    target_nested_group['pages'] = []
                    target_pages_container = target_nested_group['pages']
                break
        # If not found, create it
        if target_nested_group is None:
            target_nested_group = {'group': nested_group_name, 'pages': []}
            # Check if target_group['pages'] is already the container we want to add to
            # This logic assumes nested groups are *always* dicts within the parent's 'pages' list
            target_group['pages'].append(target_nested_group)
            target_pages_container = target_nested_group['pages']

    # Final check before returning
    if not isinstance(target_pages_container, list):
        print(
            f"严重错误: 无法为 Tab='{tab_name}', Group='{group_name}', Nested='{nested_group_name}' 获取有效的 pages 列表。")
        return None  # Indicate failure

    return target_pages_container

# --- 主逻辑 (与之前版本相同) ---


def main():
    # 1. 加载 docs.json
    try:
        with open(DOCS_JSON_PATH, 'r', encoding='utf-8') as f:
            docs_data = json.load(f)
    except FileNotFoundError:
        print(f"错误: {DOCS_JSON_PATH} 未找到。")
        return
    except json.JSONDecodeError:
        print(f"错误: {DOCS_JSON_PATH} 格式错误。")
        return

    navigation = docs_data.get('navigation', {})

    # 2. 提取现有页面 (zh)
    existing_pages, target_lang_nav = extract_existing_pages(
        navigation, LANGUAGE_CODE)
    if target_lang_nav is None:
        print(f"错误：无法在 {DOCS_JSON_PATH} 中找到语言 '{LANGUAGE_CODE}' 的导航部分。脚本终止。")
        return

    print(f"找到 {len(existing_pages)} 个已存在的 '{LANGUAGE_CODE}' 页面。")

    # 3. 扫描文件系统
    filesystem_pages = set()
    valid_files = []
    if not os.path.isdir(DOCS_DIR):
        print(f"错误: 目录 '{DOCS_DIR}' 不存在。")
        return

    for filename in os.listdir(DOCS_DIR):
        if filename.endswith(FILE_EXTENSION) and FILENAME_PATTERN.match(filename):
            page_path = get_page_path(filename)
            filesystem_pages.add(page_path)
            valid_files.append(filename)

    print(f"在 '{DOCS_DIR}' 找到 {len(filesystem_pages)} 个有效的文档文件。")

    # 4. 计算差异
    new_files_paths = filesystem_pages - existing_pages
    removed_files_paths = existing_pages - filesystem_pages

    print(f"新增文件数: {len(new_files_paths)}")
    print(f"移除文件数: {len(removed_files_paths)}")

    # 5. 移除失效页面
    if removed_files_paths:
        print("正在移除失效页面...")
        remove_obsolete_pages(target_lang_nav, removed_files_paths)
        print(f"已处理移除: {removed_files_paths}")

    # 6. 添加新页面
    if new_files_paths:
        print("正在添加新页面...")
        new_files_sorted = sorted(
            [f for f in valid_files if get_page_path(f) in new_files_paths])

        groups_to_add = defaultdict(list)
        for filename in new_files_sorted:
            match = FILENAME_PATTERN.match(filename)
            if match:
                pwxy = match.group(1)
                p, w, x, y = pwxy[0], pwxy[1], pwxy[2], pwxy[3]
                page_path = get_page_path(filename)

                group_key = (p, w, x)
                if group_key in PWX_TO_GROUP_MAP:
                    map_result = PWX_TO_GROUP_MAP[group_key]
                    # Handle potential None for nested_group_name
                    if len(map_result) == 3:
                        tab_name, group_name, nested_group_name = map_result
                    else:  # Assume (tab_name, group_name) if len is 2, though map should be consistent
                        tab_name, group_name = map_result
                        nested_group_name = None  # Explicitly None if not provided
                    groups_to_add[(tab_name, group_name, nested_group_name)].append(
                        page_path)
                else:
                    print(
                        f"警告: 文件 '{filename}' 的 PWX 前缀 ('{p}', '{w}', '{x}') 在 PWX_TO_GROUP_MAP 中没有找到映射，将跳过添加。")

        for (tab_name, group_name, nested_group_name), pages_to_append in groups_to_add.items():
            print(
                f"  添加到 Tab='{tab_name}', Group='{group_name}', Nested='{nested_group_name or '[无]'}' : {len(pages_to_append)} 个页面")
            target_pages_list = find_or_create_target_group(
                target_lang_nav, tab_name, group_name, nested_group_name)

            if isinstance(target_pages_list, list):
                for new_page in pages_to_append:
                    if new_page not in target_pages_list:
                        target_pages_list.append(new_page)
                        print(f"    + {new_page}")
            else:
                print(
                    f"错误: 未能为 Tab='{tab_name}', Group='{group_name}', Nested='{nested_group_name}' 添加页面。")

    # 7. 写回 docs.json
    try:
        with open(DOCS_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(docs_data, f, ensure_ascii=False, indent=4)
        print(f"成功更新 {DOCS_JSON_PATH}")
    except IOError:
        print(f"错误: 无法写入 {DOCS_JSON_PATH}")


if __name__ == "__main__":
    main()
