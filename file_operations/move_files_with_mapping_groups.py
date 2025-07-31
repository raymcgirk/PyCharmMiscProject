from pathlib import Path
import shutil
import psutil
import os

SOURCE_DEST_GROUPS = [
    {
        "sources": [Path("A:\\"), Path("B:\\"), Path("C:\\")],
        "destinations": [Path("D:\\")]
    },
    {
        "sources": [Path("E:\\"), Path("F:\\"), Path("G:\\")],
        "destinations": [Path("H:\\")]
    }
    # Add more groups as needed
]
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

def get_all_destination_paths() -> set[Path]:
    paths = set()
    for group in SOURCE_DEST_GROUPS:
        paths.update(group["destinations"])
    return paths

def scan_source_group(sources: list[Path], seen_files: set[tuple[str, int]]) -> list[tuple[Path, Path, os.stat_result]]:
    results = []

    for source in sources:
        print(f"Walking source directory: {source}")
        for root, dirs, files in os.walk(source):
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_DIRNAMES]

            root_path = Path(root)
            for name in files:
                file_path = root_path / name
                if should_exclude_file(file_path):
                    continue

                try:
                    file_stat = file_path.stat()
                    file_size = file_stat.st_size
                    rel_path = relative_path(file_path, source)
                    sig = (str(rel_path).lower(), file_size)

                    if sig in seen_files:
                        print(f"[SKIP] Duplicate across groups: {file_path}")
                        continue

                    seen_files.add(sig)
                    print(f"[QUEUE] {file_path}")
                    results.append((file_path, source, file_stat))
                except Exception as e:
                    print(f"[ERROR] Skipping unreadable file: {file_path} - {e}")
    return results

def should_exclude_file(file_path: Path) -> bool:
    if file_path.name.lower() in EXCLUDED_FILENAMES:
        print(f"[SKIP] Excluded filename: {file_path.name}")
        return True
    if file_path.suffix.lower() in EXCLUDED_EXTENSIONS:
        print(f"[SKIP] Excluded extension: {file_path.name}")
        return True
    return False

def move_file_to_destinations(
        file_path: Path,
        rel_path: Path,
        file_size: int,
        file_stat: os.stat_result,
        destinations: list[Path]
) -> bool:

    for dest in destinations:
        print(f"Checking destination: {dest}")
        if not has_enough_space(dest, file_size):
            print(f"Not enough space on {dest}, skipping.")
            continue

        target_path = dest / rel_path
        print(f"Preparing to move to: {target_path}")
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, target_path)

            try:
                moved_size = target_path.stat().st_size
            except Exception as e:
                print(f"[ERROR] Failed to stat files for size check: {file_path} or {target_path} - {e}")
                try:
                    target_path.unlink(missing_ok=True)
                    print(f"[CLEANUP] Deleted target after stat failure: {target_path}")
                except Exception as cleanup_error:
                    print(f"[ERROR] Could not clean up target: {cleanup_error}")
                continue

            if file_stat.st_size != moved_size:
                print(f"[ERROR] Size mismatch: {file_path} ({file_stat.st_size}) -> {target_path} ({moved_size})")
                target_path.unlink(missing_ok=True)
                continue

            try:
                file_path.unlink()
                print(f"[MOVE] {file_path} -> {target_path}")
            except Exception as e:
                print(f"[ERROR] Copied but failed to delete source {file_path}: {e}")

            return True

        except Exception as e:
            print(f"[ERROR] Failed to move {file_path} -> {target_path}: {e}")

    print(f"[WARNING] All destinations full. Skipped: {file_path}")
    return False

def process_file_group(group: dict, existing_index: set[tuple[str, int]], seen_files: set[tuple[str, int]]) -> None:
    sources = group["sources"]
    destinations = group["destinations"]

    print(f"Scanning sources: {sources}")
    all_files = scan_source_group(sources, seen_files)
    print(f"Total files to evaluate: {len(all_files)}")

    for file_path, base, file_stat in all_files:
        try:
            rel_path = relative_path(file_path, base)
            file_size = file_stat.st_size
            if already_moved(str(rel_path), file_size, existing_index):
                print(f"[SKIP] Already moved: {file_path}")
                continue
        except Exception as e:
            print(f"[ERROR] Failed to prepare file {file_path}: {e}")
            continue

        move_file_to_destinations(file_path, rel_path, file_size, file_stat, destinations)

def main():
    all_destinations = get_all_destination_paths()
    existing_index = build_existing_file_index(list(all_destinations))
    seen_files: set[tuple[str, int]] = set()

    for group in SOURCE_DEST_GROUPS:
        process_file_group(group, existing_index, seen_files)

if __name__ == "__main__":
    main()
