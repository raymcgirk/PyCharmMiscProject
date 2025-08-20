from pathlib import Path
import shutil
import psutil
import os

SOURCES = [Path("P:\\My Movies\\"), Path("O:\\My Movies\\")]
DESTINATIONS = [Path("H:\\")]
EXCLUDED_EXTENSIONS = {".srt", ".tmp", ".bak"}
EXCLUDED_FILENAMES = {"thumbs.db", ".DS_Store"}
EXCLUDED_DIRNAMES = {"#recycle"}
THRESHOLD_BYTES = 500 * 1024**3  # 500 GB

def has_enough_space(dest: Path, file_size: int) -> bool:
    usage = psutil.disk_usage(str(dest))
    return usage.free >= file_size + THRESHOLD_BYTES

def relative_path(full_path: Path, base: Path) -> Path:
    return full_path.relative_to(base)

def build_existing_file_index(destinations: list[Path]) -> set[tuple[str, int]]:
    existing_files = set()
    print("Building existing file index...")
    for dest in destinations:
        print(f"Indexing: {dest}")
        for root, dirs, files in os.walk(dest):
            root_path = Path(root)
            for name in files:
                full_path = root_path / name
                rel_path = full_path.relative_to(dest)
                try:
                    size = full_path.stat().st_size
                    existing_files.add((str(rel_path).lower(), size))
                except Exception as e:
                    print(f"[ERROR] Skipping during index: {full_path} - {e}")
    print(f"Indexed {len(existing_files)} existing files.")
    return existing_files

def already_moved(rel_path: str, size: int, existing_index: set[tuple[str, int]]) -> bool:
    return (rel_path.lower(), size) in existing_index

def retroactively_remove_empty_dirs(root_path: Path):
    print(f"Scanning for pre-existing empty folders in: {root_path}")
    for root, dirs, _ in os.walk(root_path, topdown=False):
        for d in dirs:
            dir_path = Path(root) / d
            try:
                if not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    print(f"[PRE-CLEAN] Removed empty folder: {dir_path}")
            except Exception as e:
                print(f"[ERROR] Could not remove {dir_path}: {e}")


def remove_empty_dirs_upward(start: Path, stop: Path):
    parent = start.parent
    while parent != stop and parent.exists():
        try:
            if not any(parent.iterdir()):
                parent.rmdir()
                print(f"[CLEANED] Removed empty folder: {parent}")
            else:
                break
        except Exception as e:
            print(f"[ERROR] Could not remove empty folder {parent}: {e}")
            break
        parent = parent.parent

def main():
    for source in SOURCES:
        retroactively_remove_empty_dirs(source)
    all_files: list[tuple[Path, Path]] = []
    existing_index = build_existing_file_index(DESTINATIONS)
    print(f"Scanning sources: {SOURCES}")

    for source in SOURCES:
        print(f"Walking source directory: {source}")
        for root, dirs, files in os.walk(source):
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_DIRNAMES]
            root_path = Path(root)
            for name in files:
                file_path = root_path / name
                ext = file_path.suffix.lower()
                if file_path.name.lower() in EXCLUDED_FILENAMES or ext in EXCLUDED_EXTENSIONS:
                    print(f"[SKIP] Excluded: {file_path.name}")
                    continue
                try:
                    file_path.stat()
                    print(f"[QUEUE] {file_path}")
                    all_files.append((file_path, source))
                except Exception as e:
                    print(f"[ERROR] Skipping unreadable file: {file_path} - {e}")

    print(f"Total files to evaluate: {len(all_files)}")
    for file_path, base in all_files:
        try:
            rel_path = relative_path(file_path, base)
            file_size = file_path.stat().st_size
            if already_moved(str(rel_path), file_size, existing_index):
                print(f"[SKIP] Already moved: {file_path}")
                continue
        except Exception as e:
            print(f"[ERROR] Failed to prepare file {file_path}: {e}")
            continue

        moved = False
        for dest in DESTINATIONS:
            print(f"Checking destination: {dest}")
            if not has_enough_space(dest, file_size):
                print(f"Not enough space on {dest}, skipping.")
                continue

            target_path = dest / rel_path
            print(f"Preparing to move to: {target_path}")
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, target_path)
                original_size = file_path.stat().st_size
                moved_size = target_path.stat().st_size

                if original_size != moved_size:
                    print(f"[ERROR] Size mismatch: {file_path} -> {target_path}")
                    target_path.unlink(missing_ok=True)
                    continue

                file_path.unlink()
                print(f"[MOVE] {file_path} -> {target_path}")
                remove_empty_dirs_upward(file_path, base)
                moved = True
                break

            except Exception as e:
                print(f"[ERROR] Failed to move {file_path} -> {target_path}: {e}")

        if not moved:
            print(f"[WARNING] All destinations full. Skipped: {file_path}")

    for source in SOURCES:
        remove_empty_dirs_upward(source, source)

main()
