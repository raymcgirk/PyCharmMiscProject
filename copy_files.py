import os
import shutil
import psutil

SOURCE = "Y:\\"
DESTINATIONS = ["H:\\", "I:\\", "J:\\"]
EXCLUDED_EXTENSIONS = {".srt", ".tmp", ".bak"}
EXCLUDED_FILENAMES = {"thumbs.db", ".DS_Store"}
THRESHOLD_BYTES = 500 * 1024**3  # 500 GB

def has_enough_space(dest, file_size):
    usage = psutil.disk_usage(dest)
    return usage.free >= file_size + THRESHOLD_BYTES

def relative_path(full_path):
    return os.path.relpath(full_path, SOURCE)

def already_copied(file_path, relative):
    for dest in DESTINATIONS:
        target_path = os.path.join(dest, relative)
        if os.path.exists(target_path):
            if os.path.getsize(file_path) == os.path.getsize(target_path):
                return True
    return False

def main():
    all_files = []
    for root, dirs, files in os.walk(SOURCE):
        for name in files:
            full_path = os.path.join(root, name)
            ext = os.path.splitext(name)[1].lower()
            if name.lower() in EXCLUDED_FILENAMES or ext in EXCLUDED_EXTENSIONS:
                continue

            try:
                os.path.getsize(full_path)  # Trigger OSError early if needed
                all_files.append(full_path)
            except Exception as e:
                print(f"[ERROR] Skipping unreadable file: {full_path} - {e}")

    for file_path in all_files:
        rel_path = relative_path(file_path)
        if already_copied(file_path, rel_path):
            continue

        file_size = os.path.getsize(file_path)
        copied = False
        for dest in DESTINATIONS:
            if not has_enough_space(dest, file_size):
                continue

            target_path = os.path.join(dest, rel_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            try:
                shutil.copy2(file_path, target_path)
                print(f"Copied: {file_path} -> {target_path}")
                copied = True
                break
            except Exception as e:
                print(f"[ERROR] Failed to copy {file_path} -> {target_path}: {e}")

        if not copied:
            print(f"[WARNING] All destinations full. Skipped: {file_path}")

if __name__ == "__main__":
    main()
