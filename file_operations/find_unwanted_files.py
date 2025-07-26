import os
from pathlib import Path

SEARCH_PATHS = ["H:\\", "I:\\", "J:\\"]
UNWANTED_EXTS = {".srt", ".tmp", ".bak", ".parts"}
UNWANTED_NAMES = {"thumbs.db", ".DS_Store"}

def is_unwanted(file_path: Path):
    return (file_path.name.lower() in UNWANTED_NAMES or
            file_path.suffix.lower() in UNWANTED_EXTS)

def scan_and_list():
    found = []
    for base in SEARCH_PATHS:
        for root, dirs, files in os.walk(base):
            for name in files:
                file_path = Path(root) / name
                if is_unwanted(file_path):
                    found.append(file_path)

    print(f"\nFound {len(found)} unwanted files:\n")
    for f in found:
        print(f)

    # Write to a text file for review
    with open("../unwanted_files.txt", "w", encoding="utf-8") as out:
        out.writelines(f"{f}\n" for f in found)

if __name__ == "__main__":
    scan_and_list()
