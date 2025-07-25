import os
import zipfile
from pathlib import Path

# === Config ===
SOURCE_DIR = Path(r"C:\Users\RayMc\PyCharmProjects")
BACKUP_ZIP = Path(r"X:\pycharm_projects_backup.zip")
EXCLUDE = set()  # Use to add exclusions if wanted like ".venv", ".git", etc.

def should_exclude(path: Path):
    parts = set(path.parts)
    return any(excluded in parts for excluded in EXCLUDE)

def zip_folder(source: Path, output: Path):
    if output.exists():
        output.unlink()  # Delete existing backup

    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source):
            root_path = Path(root)
            rel_root = root_path.relative_to(source)

            if should_exclude(rel_root):
                continue

            for file in files:
                file_path = root_path / file
                if should_exclude(file_path.relative_to(source)):
                    continue
                zipf.write(file_path, file_path.relative_to(source))

    print(f"Backup created: {output}")

if __name__ == "__main__":
    zip_folder(SOURCE_DIR, BACKUP_ZIP)
