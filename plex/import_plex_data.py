import os
import sqlite3
import requests
from urllib.parse import quote
from xml.etree import ElementTree

def get_available_servers():
    return [
        var[len("PLEX_TOKEN_"):]
        for var in os.environ
        if var.startswith("PLEX_TOKEN_")
    ]

# === Select Plex Server ===
servers = get_available_servers()
if not servers:
    raise RuntimeError("No PLEX_TOKEN_<server> env vars found.")

print("Available Plex servers:")
for i, name in enumerate(servers, 1):
    print(f"  {i}. {name}")

try:
    selection = int(input("Select a Plex server by number: ").strip())
    server = servers[selection - 1]
except (ValueError, IndexError):
    raise ValueError("Invalid server selection.")

PLEX_TOKEN = os.getenv(f"PLEX_TOKEN_{server}")
PLEX_BASE_URL = os.getenv(f"PLEX_BASE_URL_{server}")

# === Let user choose DB file to import from ===
import glob

db_files = sorted(glob.glob("plex_export_*.db"))
if not db_files:
    raise FileNotFoundError("No plex_export_*.db files found in current directory.")

print("\nAvailable export DBs:")
for i, db in enumerate(db_files, 1):
    print(f"  {i}. {db}")

try:
    db_choice = int(input("Select a DB to import watch history from: ").strip())
    DB_FILE = db_files[db_choice - 1]
except (ValueError, IndexError):
    raise ValueError("Invalid DB selection.")

if not PLEX_TOKEN or not PLEX_BASE_URL:
    raise EnvironmentError(f"Missing PLEX_TOKEN_{server} or PLEX_BASE_URL_{server}")

HEADERS = {'X-Plex-Token': PLEX_TOKEN}

# === Connect to Exported DB ===
if not os.path.exists(DB_FILE):
    raise FileNotFoundError(f"Exported DB not found: {DB_FILE}")

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

# === Query distinct libraries ===
cur.execute("SELECT DISTINCT library_section FROM media ORDER BY library_section")
libraries = [row[0] for row in cur.fetchall()]

print("Available libraries in exported DB:")
for i, lib in enumerate(libraries, 1):
    print(f"  {i}. {lib}")

try:
    lib_choice = int(input("Select a library to import view history into: ").strip())
    selected_library = libraries[lib_choice - 1]
except (ValueError, IndexError):
    raise ValueError("Invalid library selection.")

# === Get Plex library section key ===
res = requests.get(f"{PLEX_BASE_URL}/library/sections", headers=HEADERS)
res.raise_for_status()
sections_xml = ElementTree.fromstring(res.content)

section_key = None
for el in sections_xml.findall(".//Directory"):
    if el.attrib.get("title") == selected_library:
        section_key = el.attrib["key"]
        break

if not section_key:
    raise RuntimeError(f"Library '{selected_library}' not found on server '{server}'.")

# === Query watched items from DB for selected library ===
cur.execute("""
    SELECT title, last_viewed_at
    FROM media
    WHERE library_section = ?
    AND view_count IS NOT NULL
    AND last_viewed_at IS NOT NULL
""", (selected_library,))
watched = cur.fetchall()

print(f"📺 Found {len(watched)} watched items in '{selected_library}'")

# === Match by title and scrobble ===
success, failed = 0, 0
not_found = []

for title, last_viewed_at in watched:
    escaped = quote(title)
    search_url = f"{PLEX_BASE_URL}/library/sections/{section_key}/all?title={escaped}"
    r = requests.get(search_url, headers=HEADERS)
    r.raise_for_status()
    xml = ElementTree.fromstring(r.content)

    match = xml.find(".//Video")
    if match is not None:
        rating_key = match.attrib.get("ratingKey")
        scrobble_url = f"{PLEX_BASE_URL}/:/scrobble?key={rating_key}&identifier=com.plexapp.plugins.library"
        s = requests.get(scrobble_url, headers=HEADERS)
        if s.status_code == 200:
            print(f"✔️  Marked watched: {title}")
            success += 1
        else:
            print(f"❌ Failed to scrobble: {title} (status {s.status_code})")
            failed += 1
    else:
        print(f"🚫 No match found in Plex for: {title}")
        not_found.append(title)
        failed += 1

# === Summary ===
print("\n===== Import Summary =====")
print(f"✅ Scrobbled: {success}")
print(f"❌ Failed or Not Found: {failed}")
if not_found:
    print("\n🚫 Titles not found in Plex:")
    for t in not_found:
        print(f" - {t}")
