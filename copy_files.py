from pathlib import Path
import shutil
import psutil
import os

SOURCES = [Path("X:\\"), Path("Y:\\")]
DESTINATIONS = [Path("H:\\"), Path("I:\\"), Path("J:\\")]
EXCLUDED_EXTENSIONS = {".srt", ".tmp", ".bak"}
EXCLUDED_FILENAMES = {"thumbs.db", ".DS_Store"}
THRESHOLD_BYTES = 500 * 1024**3  # 500 GB

def has_enough_space(dest: Path, file_size: int) -> bool:
    usage = psutil.disk_usage(str(dest))
    return usage.free >= file_size + THRESHOLD_BYTES

def relative_path(full_path: Path, base: Path) -> Path:
    return full_path.relative_to(base)

def already_copied(file_path: Path, rel_path: Path) -> bool:
    for dest in DESTINATIONS:
        target_path = dest / rel_path
        if target_path.exists() and target_path.stat().st_size == file_path.stat().st_size:
            return True
    return False

def main():
    all_files: list[tuple[Path, Path]] = []
    for source in SOURCES:
        for root, dirs, files in os.walk(source):
            root_path = Path(root)
            for name in files:
                file_path = root_path / name
                ext = file_path.suffix.lower()
                if file_path.name.lower() in EXCLUDED_FILENAMES or ext in EXCLUDED_EXTENSIONS:
                    continue

                try:
                    file_path.stat()
                    all_files.append((file_path, source))
                except Exception as e:
                    print(f"[ERROR] Skipping unreadable file: {file_path} - {e}")

    for file_path, base in all_files:
        rel_path = relative_path(file_path, base)
        if already_copied(file_path, rel_path):
            continue

        file_size = file_path.stat().st_size
        copied = False
        for dest in DESTINATIONS:
            if not has_enough_space(dest, file_size):
                continue

            target_path = dest / rel_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
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
