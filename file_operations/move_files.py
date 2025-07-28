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

def already_moved(rel_path: str, size: int, existing_index: set[tuple[str, int]]) -> bool:
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
        try:
            rel_path = relative_path(file_path, base)
            try:
                file_size = file_path.stat().st_size
            except Exception as e:
                print(f"[ERROR] Could not stat {file_path} for size check: {e}")
                continue

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
            target_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(file_path, target_path)

                # Verify the file size matches
                try:
                    original_size = file_path.stat().st_size
                    moved_size = target_path.stat().st_size
                except Exception as e:
                    print(f"[ERROR] Failed to stat files for size check: {file_path} or {target_path} - {e}")
                    try:
                        target_path.unlink(missing_ok=True)
                        print(f"[CLEANUP] Deleted target after stat failure: {target_path}")
                    except Exception as cleanup_error:
                        print(f"[ERROR] Could not clean up target: {cleanup_error}")
                    continue

                if original_size != moved_size:
                    print(f"[ERROR] Size mismatch: {file_path} ({original_size}) -> {target_path} ({moved_size})")
                    target_path.unlink(missing_ok=True)
                    continue  # Try the next destination or skip

                try:
                    file_path.unlink()
                    print(f"[MOVE] {file_path} -> {target_path}")
                except Exception as e:
                    print(f"[ERROR] Copied but failed to delete source {file_path}: {e}")

                moved = True
                break

            except Exception as e:
                print(f"[ERROR] Failed to move {file_path} -> {target_path}: {e}")

        if not moved:
            print(f"[WARNING] All destinations full. Skipped: {file_path}")

if __name__ == "__main__":
    main()
