import os
import shutil
import datetime
from pathlib import Path
import sys

# Paths
source_dir =
dest_dir =
retention_days = 60

logfile = os.path.join(dest_dir, "backup_sync.log")
sys.stdout = open(logfile, "w")
sys.stderr = sys.stdout
print(f"\n[{datetime.datetime.now()}] Running backup sync job")

# Ensure destination exists
os.makedirs(dest_dir, exist_ok=True)

# File copy and update
for filename in os.listdir(source_dir):
    if filename.startswith("config-backup-") and filename.endswith(".db"):
        src_path = os.path.join(source_dir, filename)
        dst_path = os.path.join(dest_dir, filename)

        # Copy if not present or updated
        if not os.path.exists(dst_path) or os.path.getmtime(src_path) > os.path.getmtime(dst_path):
            print(f"Copying: {filename}")
            shutil.copy2(src_path, dst_path)

# Cleanup old files
cutoff = datetime.datetime.now() - datetime.timedelta(days=retention_days)

for file in Path(dest_dir).glob("config-backup-*.db"):
    modified = datetime.datetime.fromtimestamp(file.stat().st_mtime)
    if modified < cutoff:
        print(f"Deleting old backup: {file.name}")
        file.unlink()
