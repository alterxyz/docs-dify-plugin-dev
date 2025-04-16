import json
import os
import re
from collections import defaultdict

# --- 配置 ---
DOCS_JSON_PATH = 'docs.json'
DOCS_DIR = 'plugin_dev_zh'
LANGUAGE_CODE = 'zh'
FILE_EXTENSION = '.zh.mdx'
FILENAME_PATTERN = re.compile(r'^(\d{4})-\[(.*?)\]\.zh\.mdx$')

# --- PWX 到 Group 名称的映射 (根据上面的设计) ---
# (P, W, X) -> (tab_name, group_name, nested_group_name)
# 注意：这个映射需要根据你的实际分类意图进行调整和完善
PWX_TO_GROUP_MAP = {
    # P=0: 核心内容
    ('0', '1', '1'): ("核心内容", "概念与入门", "概览"),
    ('0', '1', '3'): ("核心内容", "概念与入门", "核心概念与速查"),
    ('0', '2', '1'): ("核心内容", "插件开发实践", "快速开始"),
    ('0', '2', '2'): ("核心内容", "插件开发实践", "标准开发流程"),
    ('0', '3', '1'): ("核心内容", "贡献与发布", "行为准则与规范"),
    ('0', '3', '2'): ("核心内容", "贡献与发布", "发布插件"),
    ('0', '3', '3'): ("核心内容", "贡献与发布", "常见问题解答"),
    ('0', '4', '1'): ("核心内容", "技术参考与示例", "核心规范与功能"),
    ('0', '4', '3'): ("核心内容", "技术参考与示例", "开发示例"),
    # P=9: 高级主题
    ('9', '2', '2'): ("高级主题", "高级实现技巧", "高级工具与 Agent"),  # 合并 X=2, X=3
    ('9', '2', '3'): ("高级主题", "高级实现技巧", "高级工具与 Agent"),  # 合并 X=2, X=3
    ('9', '2', '4'): ("高级主题", "高级实现技巧", "反向调用与其他"),
    ('9', '4', '3'): ("高级主题", "高级 Agent 策略", "Agent 策略插件"),
}

# --- 辅助函数 ---


def get_page_path(filename):
    """从 mdx 文件名获取 mintlify 页面路径 (去掉 .mdx 后缀)"""
    return os.path.join(DOCS_DIR, filename[:-len('.mdx')])


def extract_existing_pages(navigation_data, lang_code):
    """递归提取指定语言下所有已存在的页面路径"""
    existing_pages = set()
    lang_found = False
    if not navigation_data or 'languages' not in navigation_data:
        print("警告: 'navigation.languages' 未找到")
        return existing_pages, None  # 返回空集合和 None 表示未找到语言部分

    target_lang_nav = None
    for lang_nav in navigation_data.get('languages', []):
        if lang_nav.get('language') == lang_code:
            target_lang_nav = lang_nav
            lang_found = True
            break

    if not lang_found:
        print(f"警告: 语言 '{lang_code}' 在 docs.json 中未找到")
        return existing_pages, None  # 返回空集合和 None

    for tab in target_lang_nav.get('tabs', []):
        for group in tab.get('groups', []):
            _recursive_extract(group, existing_pages)

    return existing_pages, target_lang_nav  # 返回页面集合和找到的语言导航部分


def _recursive_extract(group_item, pages_set):
    """递归辅助函数"""
    if 'pages' in group_item:
        for page in group_item['pages']:
            if isinstance(page, str):
                pages_set.add(page)
            elif isinstance(page, dict) and 'group' in page:  # 处理嵌套 group
                _recursive_extract(page, pages_set)


def remove_obsolete_pages(navigation_data, pages_to_remove):
    """递归移除失效的页面条目"""
    if isinstance(navigation_data, dict):
        if 'pages' in navigation_data:
            new_pages = []
            for page in navigation_data['pages']:
                if isinstance(page, str):
                    if page not in pages_to_remove:
                        new_pages.append(page)
                elif isinstance(page, dict):
                    remove_obsolete_pages(
                        page, pages_to_remove)  # 递归处理嵌套 group
                    # 可选：如果递归后嵌套 group 的 pages 为空，可以考虑移除该 group
                    if page.get('pages'):  # 仅保留非空嵌套 group
                        new_pages.append(page)
                else:
                    new_pages.append(page)  # 保留非字符串和非字典项（如果有的话）
            navigation_data['pages'] = new_pages
        # 递归处理 group 内部的其他可能包含 pages 的结构
        for key, value in navigation_data.items():
            if key != 'pages' and (isinstance(value, (dict, list))):
                remove_obsolete_pages(value, pages_to_remove)

    elif isinstance(navigation_data, list):
        # 递归处理列表中的每个元素 (例如 tabs 或 groups 列表)
        new_list = []
        for item in navigation_data:
            if isinstance(item, (dict, list)):
                remove_obsolete_pages(item, pages_to_remove)
                # 可选：如果 group 处理后 pages 为空，可以考虑移除
                if isinstance(item, dict) and 'group' in item and not item.get('pages'):
                    # print(f"信息: 考虑移除空组 '{item.get('group')}'") # 暂时不移除，保留结构
                    new_list.append(item)  # 暂时保留空组
                else:
                    new_list.append(item)
            else:
                new_list.append(item)  # 保留非字典/列表项
        # 注意：不能直接修改列表长度在迭代中，所以通常不在这里直接移除item
        # 但上面逻辑是构建 new_list，所以没问题


def find_or_create_target_group(target_lang_nav, tab_name, group_name, nested_group_name):
    """查找或创建目标 Tab 和 Group 结构，返回最低层级的 pages 列表引用"""
    target_tab = None
    for tab in target_lang_nav.setdefault('tabs', []):
        if tab.setdefault('tab', '') == tab_name:
            target_tab = tab
            break
    if target_tab is None:
        target_tab = {'tab': tab_name, 'groups': []}
        target_lang_nav['tabs'].append(target_tab)

    target_group = None
    for group in target_tab.setdefault('groups', []):
        if group.setdefault('group', '') == group_name:
            target_group = group
            break
    if target_group is None:
        target_group = {'group': group_name, 'pages': []}
        target_tab['groups'].append(target_group)

    target_nested_group = None
    # pages 可以直接在 group 下，也可以在 nested group 下
    if nested_group_name:
        target_pages_container = None
        for item in target_group.setdefault('pages', []):
            if isinstance(item, dict) and item.get('group') == nested_group_name:
                target_nested_group = item
                target_pages_container = target_nested_group.setdefault(
                    'pages', [])
                break
        if target_nested_group is None:
            target_nested_group = {'group': nested_group_name, 'pages': []}
            target_group['pages'].append(target_nested_group)  # 添加新的嵌套组
            target_pages_container = target_nested_group['pages']
    else:
        # 如果没有 nested_group_name，页面直接放在顶层 group 的 pages 里
        # 确保 pages 是列表
        if not isinstance(target_group.get('pages'), list):
            target_group['pages'] = []
        target_pages_container = target_group['pages']

    return target_pages_container


# --- 主逻辑 ---
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
        # 或者可以考虑创建一个空的语言结构？取决于需求
        # target_lang_nav = {'language': LANGUAGE_CODE, 'tabs': []}
        # navigation.setdefault('languages', []).append(target_lang_nav)
        return  # 终止执行

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
            valid_files.append(filename)  # 保存原始文件名用于排序

    print(f"在 '{DOCS_DIR}' 找到 {len(filesystem_pages)} 个有效的文档文件。")

    # 4. 计算差异
    new_files_paths = filesystem_pages - existing_pages
    removed_files_paths = existing_pages - filesystem_pages

    print(f"新增文件数: {len(new_files_paths)}")
    print(f"移除文件数: {len(removed_files_paths)}")

    # 5. 移除失效页面
    if removed_files_paths:
        print("正在移除失效页面...")
        # 直接修改 target_lang_nav
        remove_obsolete_pages(target_lang_nav, removed_files_paths)
        print(f"已移除: {removed_files_paths}")

    # 6. 添加新页面
    if new_files_paths:
        print("正在添加新页面...")
        # 按 PWXY 排序新增文件
        new_files_sorted = sorted(
            [f for f in valid_files if get_page_path(f) in new_files_paths])

        # 按目标 group 分组添加
        groups_to_add = defaultdict(list)
        for filename in new_files_sorted:
            match = FILENAME_PATTERN.match(filename)
            if match:
                pwxy = match.group(1)
                p, w, x, y = pwxy[0], pwxy[1], pwxy[2], pwxy[3]
                page_path = get_page_path(filename)

                # 查找映射
                group_key = (p, w, x)
                if group_key in PWX_TO_GROUP_MAP:
                    tab_name, group_name, nested_group_name = PWX_TO_GROUP_MAP[group_key]
                    groups_to_add[(tab_name, group_name, nested_group_name)].append(
                        page_path)
                else:
                    print(
                        f"警告: 文件 '{filename}' 的 PWX 前缀 ('{p}', '{w}', '{x}') 在 PWX_TO_GROUP_MAP 中没有找到映射，将跳过添加。")

        # 将分组后的新页面添加到 docs.json
        for (tab_name, group_name, nested_group_name), pages_to_append in groups_to_add.items():
            print(
                f"  添加到 Tab='{tab_name}', Group='{group_name}', Nested='{nested_group_name}': {len(pages_to_append)} 个页面")
            target_pages_list = find_or_create_target_group(
                target_lang_nav, tab_name, group_name, nested_group_name)

            # 检查是否是列表，以防万一 find_or_create 出错或结构不符合预期
            if isinstance(target_pages_list, list):
                # 将排序好的新页面追加到目标列表末尾
                for new_page in pages_to_append:
                    if new_page not in target_pages_list:  # 避免重复添加（理论上不应发生）
                        target_pages_list.append(new_page)
                        print(f"    + {new_page}")
            else:
                print(
                    f"错误：无法为 Tab='{tab_name}', Group='{group_name}', Nested='{nested_group_name}' 找到或创建有效的 pages 列表。")

    # 7. 写回 docs.json
    try:
        with open(DOCS_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(docs_data, f, ensure_ascii=False,
                      indent=4)  # 使用 indent=4 保持格式
        print(f"成功更新 {DOCS_JSON_PATH}")
    except IOError:
        print(f"错误: 无法写入 {DOCS_JSON_PATH}")


if __name__ == "__main__":
    main()
