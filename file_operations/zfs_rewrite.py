import os
import shutil
import hashlib
import sys
import argparse
from datetime import datetime

log_file = None

def log(message):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {message}"
    print(line)
    if log_file:
        print(line, file=log_file)

def hash_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def rewrite_file(file_path, dry_run=False):
    temp_path = file_path + ".zfsrewrite"
    done_marker = file_path + ".zfsrewrite.done"

    if os.path.exists(done_marker):
        log(f"[SKIP] Already rewritten: {file_path}")
        return

    if os.path.exists(temp_path):
        log(f"[CLEANUP] Removing stale temp file: {temp_path}")
        try:
            os.remove(temp_path)
        except Exception as e:
            log(f"[ERROR] Failed to remove stale temp file: {e}")
            return

    if dry_run:
        log(f"[DRY-RUN] Would rewrite: {file_path}")
        return

    try:
        log(f"[COPY] {file_path} → {temp_path}")
        shutil.copy2(file_path, temp_path)

        original_hash = hash_file(file_path)
        temp_hash = hash_file(temp_path)

        if original_hash != temp_hash:
            log(f"[ERROR] Hash mismatch! Aborting rewrite: {file_path}")
            os.remove(temp_path)
            return

        log(f"[DELETE] {file_path}")
        os.remove(file_path)

        log(f"[RENAME] {temp_path} → {file_path}")
        os.rename(temp_path, file_path)

        final_hash = hash_file(file_path)
        if final_hash != original_hash:
            log(f"[ERROR] Final verification failed: {file_path}")
            return

        with open(done_marker, 'w') as f:
            f.write("ok\n")

        log(f"[OK] Successfully rewritten: {file_path}")

    except Exception as e:
        log(f"[EXCEPTION] Error processing {file_path}: {e}")

def extract_pool_name(pool_path):
    parts = os.path.normpath(pool_path).split(os.sep)
    if len(parts) >= 3 and parts[1] == "mnt":
        return parts[2]
    return os.path.basename(pool_path.rstrip("/"))

def process_pool_recursively(pool_path, dry_run=False):
    for root, dirs, files in os.walk(pool_path):
        if not files:
            continue
        relative = os.path.relpath(root, pool_path)
        log(f"\n--- Processing directory: {relative} ---\n")
        for name in files:
            full_path = os.path.join(root, name)
            try:
                if os.path.islink(full_path):
                    continue
                rewrite_file(full_path, dry_run=dry_run)
            except Exception as e:
                log(f"[EXCEPTION] {full_path}: {e}")

def get_script_dir():
    return os.path.dirname(os.path.realpath(__file__))

def main():
    parser = argparse.ArgumentParser(description="ZFS in-place rewrite tool with resume and logging")
    parser.add_argument("pool_path", help="Path to mounted ZFS pool (e.g. /mnt/my-pool)")
    parser.add_argument("--dry-run", action="store_true", help="Do a dry run without modifying files")

    args = parser.parse_args()
    pool_path = args.pool_path
    dry_run = args.dry_run

    if not os.path.isdir(pool_path):
        print(f"Invalid path: {pool_path}")
        sys.exit(1)

    pool_name = extract_pool_name(pool_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_dir = get_script_dir()
    log_filename = f"zfs_rewrite_{pool_name}_{timestamp}.log"
    log_path = os.path.join(script_dir, log_filename)

    global log_file
    try:
        log_file = open(log_path, "w")
        log(f"Started ZFS rewrite on pool: {pool_name}")
        log(f"Target path: {pool_path}")
        log(f"Log file: {log_path}")
        if dry_run:
            log("[MODE] Dry-run only — no files will be modified.")
        process_pool_recursively(pool_path, dry_run=dry_run)
        log("Completed rewrite.")
    finally:
        if log_file:
            log_file.close()

if __name__ == "__main__":
    main()
