import json
import os
import re
from collections import defaultdict

# instruction: If a major update is made, redeploy and manually delete the implementation: `"navigation": {"languages": [{"language": "en","tabs": [empty]`
# --- Configuration ---
DOCS_JSON_PATH = 'docs.json'
DOCS_DIR = 'plugin_dev_en'  # Changed directory name
LANGUAGE_CODE = 'en'        # Changed language code
FILE_EXTENSION = '.en.mdx'  # Changed file extension
# Update regex to match '0000-Title.en.mdx' format
FILENAME_PATTERN = re.compile(r'^(\d{4})-(.*?)\.en\.mdx$') # Changed regex

# --- PWX to Group Name Mapping (New Two-Tab Structure - English) ---
# (P, W, X) -> (tab_name, group_name, nested_group_name)
PWX_TO_GROUP_MAP = {
    # Tab: Plugin Development (Merged original P=0 and P=9, removed 013x, 041x)
    #   Group: Concepts & Getting Started
    ('0', '1', '1'): ("Plugin Development", "Concepts & Getting Started", "Overview"), # <-- Keep at the beginning of the main flow
    #   Group: Development Practices
    ('0', '2', '1'): ("Plugin Development", "Development Practices", "Quick Start"),
    ('0', '2', '2'): ("Plugin Development", "Development Practices", "Developing Dify Plugins"),
    #   Group: Contribution & Publishing
    ('0', '3', '1'): ("Plugin Development", "Contribution & Publishing", "Code of Conduct & Standards"),
    ('0', '3', '2'): ("Plugin Development", "Contribution & Publishing", "Publishing & Listing"),
    ('0', '3', '3'): ("Plugin Development", "Contribution & Publishing", "FAQ"),
    #   Group: Examples & Use Cases (Original 043x)
    ('0', '4', '3'): ("Plugin Development", "Examples & Use Cases", "Development Examples"), # <-- Keep in the main flow
    #   Group: Advanced Development (Original P=9 content)
    ('9', '2', '2'): ("Plugin Development", "Advanced Development", "Extension & Agent"), # <-- P=9 content integrated
    ('9', '2', '3'): ("Plugin Development", "Advanced Development", "Extension & Agent"), # <-- P=9 content integrated
    ('9', '4', '3'): ("Plugin Development", "Advanced Development", "Extension & Agent"), # <-- P=9 content integrated
    ('9', '2', '4'): ("Plugin Development", "Advanced Development", "Reverse Calling"),   # <-- P=9 content integrated

    # Tab: Reference & Specifications (New Tab, includes original 013x, 041x)
    #   Group: Core Concepts & Reference (Original 013x)
    ('0', '1', '3'): ("Reference & Specifications", "Core Concepts & Reference", None), # <-- Moved to new tab, no nested group
    #   Group: Core Specifications & Features (Original 041x)
    ('0', '4', '1'): ("Reference & Specifications", "Core Specifications & Features", None), # <-- Moved to new tab, no nested group
    # Note: If 013x or 041x have many files, they can also have Nested Groups,
    # e.g., ('0', '1', '3'): ("Reference & Specifications", "Quick Reference", "Core Concepts"),
    # ('0', '4', '1'): ("Reference & Specifications", "Technical Specifications", "Core Features")
    # For now, they are placed directly under the Group (nested_group_name=None)
}


# --- Helper Functions (Same logic as the previous version) ---
def get_page_path(filename):
    """Get the mintlify page path from the mdx filename (remove .mdx suffix)"""
    # Adjust suffix length based on the new FILE_EXTENSION
    return os.path.join(DOCS_DIR, filename[:-len('.mdx')])


def extract_existing_pages(navigation_data, lang_code):
    """Recursively extract all existing page paths for the specified language"""
    existing_pages = set()
    lang_found = False
    if not navigation_data or 'languages' not in navigation_data:
        print("Warning: 'navigation.languages' not found")
        return existing_pages, None

    target_lang_nav = None
    for lang_nav in navigation_data.get('languages', []):
        if lang_nav.get('language') == lang_code:
            target_lang_nav = lang_nav
            lang_found = True
            break

    if not lang_found:
        print(f"Warning: Language '{lang_code}' not found in docs.json")
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
    """Recursive helper function"""
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
    """Recursively remove obsolete page entries (robustness slightly improved)"""
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
                        print(f"Info: Nested group '{page.get('group')}' is empty after cleaning, structure kept.")
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
                    print(f"Info: Top-level group '{item.get('group')}' is empty after cleaning, structure kept.")
                    # navigation_data.pop(i) # Uncomment to remove empty top-level groups
                    # continue # Skip increment if item is removed
                i += 1
            elif isinstance(item, list):  # Recurse into nested lists if any
                remove_obsolete_pages(item, pages_to_remove)
                i += 1
            else:
                i += 1


def find_or_create_target_group(target_lang_nav, tab_name, group_name, nested_group_name):
    """Find or create the target Tab and Group structure, return a reference to the lowest level pages list (robustness slightly improved)"""
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
            f"Critical Error: Could not get a valid pages list for Tab='{tab_name}', Group='{group_name}', Nested='{nested_group_name}'.")
        return None  # Indicate failure

    return target_pages_container

# --- Main Logic (Same structure as the previous version) ---


def main():
    # 1. Load docs.json
    try:
        with open(DOCS_JSON_PATH, 'r', encoding='utf-8') as f:
            docs_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {DOCS_JSON_PATH} not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: {DOCS_JSON_PATH} format error.")
        return

    navigation = docs_data.get('navigation', {})

    # 2. Extract existing pages (en)
    existing_pages, target_lang_nav = extract_existing_pages(
        navigation, LANGUAGE_CODE)
    if target_lang_nav is None:
        print(f"Error: Could not find navigation section for language '{LANGUAGE_CODE}' in {DOCS_JSON_PATH}. Script terminated.")
        return

    print(f"Found {len(existing_pages)} existing '{LANGUAGE_CODE}' pages.")

    # 3. Scan filesystem
    filesystem_pages = set()
    valid_files = []
    if not os.path.isdir(DOCS_DIR):
        print(f"Error: Directory '{DOCS_DIR}' does not exist.")
        return

    for filename in os.listdir(DOCS_DIR):
        if filename.endswith(FILE_EXTENSION) and FILENAME_PATTERN.match(filename):
            page_path = get_page_path(filename)
            filesystem_pages.add(page_path)
            valid_files.append(filename)

    print(f"Found {len(filesystem_pages)} valid document files in '{DOCS_DIR}'.")

    # 4. Calculate differences
    new_files_paths = filesystem_pages - existing_pages
    removed_files_paths = existing_pages - filesystem_pages

    print(f"New files count: {len(new_files_paths)}")
    print(f"Removed files count: {len(removed_files_paths)}")

    # 5. Remove obsolete pages
    if removed_files_paths:
        print("Removing obsolete pages...")
        remove_obsolete_pages(target_lang_nav, removed_files_paths)
        print(f"Processed removals: {removed_files_paths}")

    # 6. Add new pages
    if new_files_paths:
        print("Adding new pages...")
        new_files_sorted = sorted(
            [f for f in valid_files if get_page_path(f) in new_files_paths])

        groups_to_add = defaultdict(list)
        for filename in new_files_sorted:
            match = FILENAME_PATTERN.match(filename)
            if match:
                # Assuming the 4-digit prefix remains the same structure
                pwxy = match.group(1)
                if len(pwxy) == 4: # Basic check for 4 digits
                    p, w, x, y = pwxy[0], pwxy[1], pwxy[2], pwxy[3] # Assuming y is not used for mapping key
                    page_path = get_page_path(filename)

                    group_key = (p, w, x)
                    if group_key in PWX_TO_GROUP_MAP:
                        map_result = PWX_TO_GROUP_MAP[group_key]
                        # Handle potential None for nested_group_name
                        if len(map_result) == 3:
                            tab_name, group_name, nested_group_name = map_result
                        else: # Assume (tab_name, group_name) if len is 2
                            tab_name, group_name = map_result
                            nested_group_name = None # Explicitly None if not provided
                        groups_to_add[(tab_name, group_name, nested_group_name)].append(
                            page_path)
                    else:
                        print(
                            f"Warning: PWX prefix ('{p}', '{w}', '{x}') for file '{filename}' not found in PWX_TO_GROUP_MAP. Skipping add.")
                else:
                     print(f"Warning: Filename '{filename}' does not match expected 'NNNN-' prefix format. Skipping.")


        for (tab_name, group_name, nested_group_name), pages_to_append in groups_to_add.items():
            print(
                f"  Adding to Tab='{tab_name}', Group='{group_name}', Nested='{nested_group_name or '[None]'}' : {len(pages_to_append)} pages")
            target_pages_list = find_or_create_target_group(
                target_lang_nav, tab_name, group_name, nested_group_name)

            if isinstance(target_pages_list, list):
                for new_page in pages_to_append:
                    if new_page not in target_pages_list:
                        target_pages_list.append(new_page)
                        print(f"    + {new_page}")
            else:
                print(
                    f"Error: Failed to add pages for Tab='{tab_name}', Group='{group_name}', Nested='{nested_group_name}'.")

    # 7. Write back to docs.json
    try:
        with open(DOCS_JSON_PATH, 'w', encoding='utf-8') as f:
            # Use ensure_ascii=False to keep non-ASCII chars if any exist in other languages
            json.dump(docs_data, f, ensure_ascii=False, indent=4)
        print(f"Successfully updated {DOCS_JSON_PATH}")
    except IOError:
        print(f"Error: Could not write to {DOCS_JSON_PATH}")


if __name__ == "__main__":
    main()
