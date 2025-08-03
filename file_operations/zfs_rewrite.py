import os
import hashlib
import sys
import argparse
from datetime import datetime
import subprocess

log_file = None

def log(message):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {message}"
    print(line)
    if log_file:
        print(line, file=log_file, flush=True)

def hash_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def rsync_copy(src, dst):
    """Use rsync to copy files while preserving all metadata"""
    result = subprocess.run([
        "rsync", "-aXAH", "--inplace", "--no-compress", "--progress", src, dst
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"rsync failed: {result.stderr.strip()}")

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
        log(f"[STEP] Copying original → temp: {file_path} → {temp_path}")
        rsync_copy(file_path, temp_path)
        log(f"[STEP] Copy successful")

        log(f"[STEP] Hashing original file")
        original_hash = hash_file(file_path)
        log(f"[STEP] Hashing temp file")
        temp_hash = hash_file(temp_path)

        if original_hash != temp_hash:
            log(f"[ERROR] Hash mismatch after copy. Aborting rewrite: {file_path}")
            os.remove(temp_path)
            return
        log(f"[STEP] Hash match verified after copy")

        log(f"[STEP] Deleting original file: {file_path}")
        os.remove(file_path)
        log(f"[STEP] Original file deleted")

        log(f"[STEP] Renaming temp → original: {temp_path} → {file_path}")
        os.rename(temp_path, file_path)
        log(f"[STEP] Rename successful")

        log(f"[STEP] Verifying final file hash")
        final_hash = hash_file(file_path)
        if final_hash != original_hash:
            log(f"[ERROR] Final hash mismatch after rename: {file_path}")
            return
        log(f"[STEP] Final hash verified")

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
                if full_path.endswith(".zfsrewrite") or full_path.endswith(".zfsrewrite.done"):
                    log(f"[SKIP] Temp or marker file: {full_path}")
                    continue
                rewrite_file(full_path, dry_run=dry_run)
            except Exception as e:
                log(f"[EXCEPTION] {full_path}: {e}")

def get_script_dir():
    return os.path.dirname(os.path.realpath(__file__))

def cleanup_done_markers(pool_path):
    log("")
    log("=== Post-Processing Cleanup: Removing .zfsrewrite.done markers ===")
    count = 0
    for root, dirs, files in os.walk(pool_path):
        for name in files:
            if name.endswith(".zfsrewrite.done"):
                marker_path = os.path.join(root, name)
                try:
                    os.remove(marker_path)
                    count += 1
                except Exception as e:
                    log(f"[WARNING] Failed to delete marker {marker_path}: {e}")
    log(f"Removed {count} .zfsrewrite.done files.")
    log("=== Cleanup complete ===")

    # 🔍 Post-cleanup validation scan
    log("")
    log("=== Validating marker cleanup ===")
    residuals = []
    for root, dirs, files in os.walk(pool_path):
        for name in files:
            if name.endswith(".zfsrewrite") or name.endswith(".zfsrewrite.done"):
                residuals.append(os.path.join(root, name))

    if residuals:
        log(f"[WARNING] {len(residuals)} .zfsrewrite-related files still found after cleanup.")
        for path in residuals[:10]:  # Log first 10 for inspection
            log(f" - {path}")
        if len(residuals) > 10:
            log(f"...and {len(residuals) - 10} more not shown")
    else:
        log("Scan complete: 0 zfsrewrite files found.")
    log("=========================================\n")

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

    # Dynamically use script location for log file
    script_dir = get_script_dir()
    log_filename = f"zfs_rewrite_{pool_name}_{timestamp}.log"
    log_path = os.path.join(script_dir, log_filename)

    global log_file
    try:
        log_file = open(log_path, "w")
    except Exception as e:
        print(f"[FATAL] Could not create log file at {log_path}: {e}")
        sys.exit(1)

    log(f"Started ZFS rewrite on pool: {pool_name}")
    log(f"Target path: {pool_path}")
    log(f"Log file: {log_path}")
    if dry_run:
        log("[MODE] Dry-run only — no files will be modified.")

    try:
        process_pool_recursively(pool_path, dry_run=dry_run)
        if not dry_run:
            cleanup_done_markers(pool_path)
        log("Completed rewrite.")
    finally:
        if log_file:
            log_file.close()

if __name__ == "__main__":
    main()
