from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import shutil
import psutil
import os

SOURCES = [Path("X:\\"), Path("Y:\\"), Path("Z:\\")]
DESTINATIONS = [Path("H:\\"), Path("I:\\"), Path("J:\\")]
EXCLUDED_EXTENSIONS = {".srt", ".tmp", ".bak"}
EXCLUDED_FILENAMES = {"thumbs.db", ".DS_Store"}
EXCLUDED_DIRNAMES = {"#recycle"}
THRESHOLD_BYTES = 500 * 1024**3  # 500 GB
MAX_WORKERS = 3

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

def move_file(file_path: Path, base: Path, destinations: list[Path], existing_index: set[tuple[str, int]]):
    rel_path = relative_path(file_path, base)
    size = file_path.stat().st_size

    if already_moved(str(rel_path), size, existing_index):
        print(f"[SKIP] Already moved: {file_path}")
        return

    for dest in destinations:
        if not has_enough_space(dest, size):
            continue

        target_path = dest / rel_path
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, target_path)
            file_path.unlink()
            print(f"[MOVE] {file_path} -> {target_path}")
            return
        except Exception as e:
            print(f"[ERROR] Failed to move {file_path} -> {target_path}: {e}")
    print(f"[WARNING] All destinations full. Skipped: {file_path}")

def main():
    all_files: list[tuple[Path, Path]] = []

    # Build index once at the beginning
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
                if file_path.name.lower() in EXCLUDED_FILENAMES:
                    print(f"[SKIP] Excluded filename: {file_path.name}")
                    continue
                if ext in EXCLUDED_EXTENSIONS:
                    print(f"[SKIP] Excluded extension: {file_path.name}")
                    continue

                try:
                    file_path.stat()
                    print(f"[QUEUE] {file_path}")
                    all_files.append((file_path, source))
                except Exception as e:
                    print(f"[ERROR] Skipping unreadable file: {file_path} - {e}")

    print(f"Total files to evaluate: {len(all_files)}")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(move_file, file_path, base, DESTINATIONS, existing_index)
            for file_path, base in all_files
        ]
        for _ in as_completed(futures):
            pass


if __name__ == "__main__":
    main()
