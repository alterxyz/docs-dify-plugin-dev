\
import os
import re
import yaml
import sys

# --- Path Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Configuration ---
# Specify the directory containing the MDX files to process
# Example: TARGET_DIR = os.path.join(BASE_DIR, "plugin_dev_zh")
# Use command line argument or default to "plugin_dev_zh"
if len(sys.argv) > 1:
    TARGET_DIR_NAME = sys.argv[1]
else:
    TARGET_DIR_NAME = "plugin_dev_en" # en or zh

TARGET_DIR = os.path.join(BASE_DIR, TARGET_DIR_NAME)

# --- Helper Functions ---

def extract_front_matter(content):
    """Extracts YAML front matter and Markdown content."""
    match = re.match(r"^\s*---\s*$(.*?)^---\s*$(.*)", content, re.DOTALL | re.MULTILINE)
    if match:
        yaml_str = match.group(1).strip()
        markdown_content = match.group(2).strip()
        try:
            front_matter = yaml.safe_load(yaml_str)
            if front_matter is None:
                return {}, markdown_content # Return empty dict if front matter is empty
            return (
                front_matter if isinstance(front_matter, dict) else {}
            ), markdown_content
        except yaml.YAMLError as e:
            print(f"  [Error] YAML Parsing Failed: {e}")
            return None, content # Indicate error by returning None for front_matter
    else:
        return {}, content # No front matter found


# --- Main Processing Function ---

def process_markdown_files(target_dir):
    """
    Processes mdx files in place, renaming 'summary' to 'description' in front matter.
    """
    print(f"Starting processing in directory: {target_dir}")
    if not os.path.isdir(target_dir):
        print(f"[Error] Target directory not found or is not a directory: {target_dir}")
        return

    processed_count = 0
    modified_count = 0
    skipped_count = 0
    error_count = 0

    all_files = [
        os.path.join(root, file)
        for root, _, files in os.walk(target_dir)
        for file in files
        if file.lower().endswith(".mdx")
    ]
    total_files = len(all_files)
    print(f"Found {total_files} MDX files to process.")

    for filepath in all_files:
        relative_path = os.path.relpath(filepath, BASE_DIR).replace(os.sep, "/")
        print(f"\nProcessing: {relative_path}")
        processed_count += 1

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            front_matter, markdown_content = extract_front_matter(content)

            if front_matter is None:
                print("  [Skipping] YAML Error in file.")
                error_count += 1
                continue

            if not isinstance(front_matter, dict):
                 print(f"  [Skipping] Front matter is not a dictionary (type: {type(front_matter)}).")
                 skipped_count += 1
                 continue

            needs_update = False
            if "summary" in front_matter:
                if "description" not in front_matter:
                    print("  [Action] Renaming 'summary' to 'description'.")
                    front_matter["description"] = front_matter.pop("summary")
                    needs_update = True
                else:
                    print("  [Warning] Both 'summary' and 'description' exist. Keeping 'description', removing 'summary'.")
                    front_matter.pop("summary") # Remove summary if description already exists
                    needs_update = True # Still need to write the file without summary
            else:
                print("  [Skipping] No 'summary' field found.")
                skipped_count += 1
                continue # Skip if no summary field

            if needs_update:
                try:
                    # Use sort_keys=False to preserve order as much as possible
                    new_yaml_str = yaml.dump(
                        front_matter,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False,
                    )
                except Exception as dump_error:
                    print(f"  [Error] Failed to dump updated YAML: {dump_error}")
                    error_count += 1
                    continue

                new_content = f"---\n{new_yaml_str}---\n\n{markdown_content}"

                # Write changes back to the original file
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print("  [Success] File updated.")
                modified_count += 1
            else:
                 # This case should ideally not be reached due to the 'continue' above
                 # but kept for logical completeness.
                 skipped_count += 1


        except FileNotFoundError:
            print(f"  [Error] File not found during processing: {filepath}")
            error_count += 1
        except Exception as e:
            print(f"  [Error] Unexpected error processing file '{relative_path}': {e}")
            import traceback
            traceback.print_exc()
            error_count += 1

        if processed_count % 10 == 0 or processed_count == total_files:
            print(f"Progress: {processed_count}/{total_files} files checked", end='\r')

    print("\n") # Newline after progress counter
    # --- Final Report ---
    print("\n--- Processing Complete ---")
    print(f"Checked: {processed_count} files")
    print(f"Modified ('summary' -> 'description'): {modified_count} files")
    print(f"Skipped (no 'summary' or not dict): {skipped_count} files")
    print(f"Errors encountered: {error_count} files")
    print("-" * 27)


if __name__ == "__main__":
    if not os.path.exists(TARGET_DIR):
         print(f"Error: Target directory '{TARGET_DIR_NAME}' not found in {BASE_DIR}.")
         print("Please specify a valid directory name as a command-line argument or ensure the default exists.")
    else:
        process_markdown_files(TARGET_DIR)

