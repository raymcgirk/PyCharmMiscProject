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

def already_copied(rel_path: str, size: int, existing_index: set[tuple[str, int]]) -> bool:
    return (rel_path.lower(), size) in existing_index

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
    for file_path, base in all_files:
        rel_path = relative_path(file_path, base)
        if already_copied(str(rel_path), file_path.stat().st_size, existing_index):
            print(f"[SKIP] Already copied: {file_path}")
            continue

        file_size = file_path.stat().st_size
        copied = False
        for dest in DESTINATIONS:
            print(f"Checking destination: {dest}")
            if not has_enough_space(dest, file_size):
                print(f"Not enough space on {dest}, skipping.")
                continue

            target_path = dest / rel_path
            print(f"Preparing to copy to: {target_path}")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(file_path, target_path)
                print(f"[COPY] {file_path} -> {target_path}")
                copied = True
                break
            except Exception as e:
                print(f"[ERROR] Failed to copy {file_path} -> {target_path}: {e}")

        if not copied:
            print(f"[WARNING] All destinations full. Skipped: {file_path}")

if __name__ == "__main__":
    main()
