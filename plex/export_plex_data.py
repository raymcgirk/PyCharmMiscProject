import os
import requests
import sqlite3
from xml.etree import ElementTree
from tqdm import tqdm

def get_available_servers():
    return [
        server_key[len("PLEX_TOKEN_"):]
        for server_key in os.environ
        if server_key.startswith("PLEX_TOKEN_")
    ]

available_servers = get_available_servers()

if not available_servers:
    raise EnvironmentError("No Plex server environment variables found. Please run setup_plex_env.py first.")

print("Available Plex servers:")
for idx, name in enumerate(available_servers, 1):
    print(f"  {idx}. {name}")

try:
    choice = int(input("Enter the number of the server to use: ").strip())
    selected = available_servers[choice - 1]
except (ValueError, IndexError):
    raise ValueError("Invalid selection. Please enter a valid number from the list.")

PLEX_TOKEN = os.getenv(f"PLEX_TOKEN_{selected}")
PLEX_BASE_URL = os.getenv(f"PLEX_BASE_URL_{selected}")

if not PLEX_TOKEN or not PLEX_BASE_URL:
    raise EnvironmentError(f"Missing env variables for {selected}: PLEX_TOKEN_{selected} and/or PLEX_BASE_URL_{selected}")

HEADERS = {'X-Plex-Token': PLEX_TOKEN}
DB_FILE = f"plex_export_{selected}.db"

# Setup SQLite
conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()
cur.execute('''
CREATE TABLE IF NOT EXISTS media (
    rating_key TEXT PRIMARY KEY,
    title TEXT,
    library_section TEXT,
    guid TEXT,
    file_path TEXT,
    duration INTEGER,
    view_count INTEGER,
    last_viewed_at INTEGER,
    view_offset INTEGER,
    user_rating REAL
)
''')
conn.commit()

def get_libraries():
    url = f'{PLEX_BASE_URL}/library/sections'
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    xml = ElementTree.fromstring(res.content)
    return [(el.attrib['key'], el.attrib['title']) for el in xml.findall('.//Directory')]

def get_episodes(show_rating_key):
    url = f"{PLEX_BASE_URL}/library/metadata/{show_rating_key}/allLeaves"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return ElementTree.fromstring(res.content)

def get_items(library_key):
    all_items = []
    start = 0
    batch_size = 1000

    while True:
        url = (
            f'{PLEX_BASE_URL}/library/sections/{library_key}/all'
            f'?X-Plex-Container-Start={start}&X-Plex-Container-Size={batch_size}'
        )
        res = requests.get(url, headers=HEADERS)
        res.raise_for_status()
        xml = ElementTree.fromstring(res.content)

        library_items = xml.findall('.//Video') + xml.findall('.//Directory')
        if not library_items:
            break  # No more to fetch

        all_items.extend(library_items)
        start += batch_size

    return all_items

def get_metadata(rating_key):
    url = f'{PLEX_BASE_URL}/library/metadata/{rating_key}'
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return ElementTree.fromstring(res.content)

def extract_file_path(metadata_xml):
    media = metadata_xml.find('.//Media')
    if media is not None:
        part = media.find('Part')
        if part is not None:
            return part.attrib.get('file')
    return None

def export_plex_library():
    print("📡 Connecting to Plex...")
    libraries = get_libraries()

    for key, title in libraries:
        print(f"\n📁 Scanning library: {title}")
        items = get_items(key)

        for export_item in tqdm(items, desc=f"Exporting {title}"):
            try:
                item_type = export_item.attrib.get("type")

                if item_type == "show":
                    episode_xml = get_episodes(export_item.attrib["ratingKey"])
                    for episode in episode_xml.findall(".//Video"):
                        process_item(episode, title)
                else:
                    process_item(export_item, title)

            except Exception as e:
                print(
                    f"⚠️ Error processing item {export_item.attrib.get('title', 'Unknown')} (type: {export_item.attrib.get('type')}): {e}"
                )

    export_playlists()

    print("\n✅ Export complete. Data saved to", DB_FILE)
    conn.close()

def export_playlists():
    print("\n🎶 Exporting playlists...")

    cur.execute('''
    CREATE TABLE IF NOT EXISTS playlists (
        rating_key TEXT PRIMARY KEY,
        title TEXT,
        playlist_type TEXT,
        leaf_count INTEGER,
        smart INTEGER,
        duration INTEGER,
        added_at INTEGER,
        updated_at INTEGER,
        summary TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS playlist_items (
        playlist_rating_key TEXT,
        item_rating_key TEXT,
        item_guid TEXT,
        item_title TEXT,
        item_type TEXT,
        file_path TEXT,
        view_count INTEGER,
        last_viewed_at INTEGER,
        view_offset INTEGER,
        user_rating REAL,
        added_at INTEGER,
        originally_available_at INTEGER,
        PRIMARY KEY (playlist_rating_key, item_rating_key)
    )
    ''')
    conn.commit()

    url = f"{PLEX_BASE_URL}/playlists"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    xml = ElementTree.fromstring(res.content)
    playlists = xml.findall(".//Playlist")

    print(f"📋 Found {len(playlists)} playlists to export.")

    for pl in tqdm(playlists, desc="Playlists"):
        pl_data = {
            'rating_key': pl.attrib.get('ratingKey'),
            'title': pl.attrib.get('title'),
            'playlist_type': pl.attrib.get('playlistType'),
            'leaf_count': int(pl.attrib.get('leafCount', 0)),
            'smart': int(pl.attrib.get('smart', '0')),
            'duration': int(pl.attrib.get('duration', 0)),
            'added_at': int(pl.attrib.get('addedAt', 0)),
            'updated_at': int(pl.attrib.get('updatedAt', 0)),
            'summary': pl.attrib.get('summary', '')
        }

        cur.execute('''
        INSERT OR REPLACE INTO playlists
        (rating_key, title, playlist_type, leaf_count, smart, duration, added_at, updated_at, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pl_data['rating_key'], pl_data['title'], pl_data['playlist_type'],
            pl_data['leaf_count'], pl_data['smart'], pl_data['duration'],
            pl_data['added_at'], pl_data['updated_at'], pl_data['summary']
        ))
        conn.commit()

        # Get playlist items
        pl_items_url = f"{PLEX_BASE_URL}/playlists/{pl_data['rating_key']}/items"
        pl_items_res = requests.get(pl_items_url, headers=HEADERS)
        pl_items_res.raise_for_status()
        pl_xml = ElementTree.fromstring(pl_items_res.content)
        pl_media_items = pl_xml.findall('.//Video') + pl_xml.findall('.//Track')

        if not pl_media_items:
            print(f"⚠️ Playlist '{pl_data['title']}' is empty.")
        else:
            print(f"✅ Saved playlist: '{pl_data['title']}' with {len(pl_media_items)} items:")
            for item in pl_media_items:
                print(f"   - {item.attrib.get('title') or item.attrib.get('grandparentTitle')}")

        for item in pl_media_items:
            rating_key = item.attrib.get('ratingKey')
            meta_xml = get_metadata(rating_key)
            file_path = extract_file_path(meta_xml)
            cur.execute('''
            INSERT OR REPLACE INTO playlist_items (
                playlist_rating_key, item_rating_key, item_guid, item_title, item_type,
                file_path, view_count, last_viewed_at, view_offset, user_rating,
                added_at, originally_available_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pl_data['rating_key'],
                rating_key,
                item.attrib.get('guid'),
                item.attrib.get('title') or item.attrib.get('grandparentTitle'),
                item.attrib.get('type'),
                file_path,
                item.attrib.get('viewCount'),
                item.attrib.get('lastViewedAt'),
                item.attrib.get('viewOffset'),
                item.attrib.get('userRating'),
                item.attrib.get('addedAt'),
                item.attrib.get('originallyAvailableAt')
            ))
        conn.commit()

def process_item(item, section_title):
    data = {
        'rating_key': item.attrib.get('ratingKey'),
        'title': item.attrib.get('title') or item.attrib.get('grandparentTitle'),
        'library_section': section_title,
        'guid': item.attrib.get('guid'),
        'duration': item.attrib.get('duration'),
        'view_count': item.attrib.get('viewCount'),
        'last_viewed_at': item.attrib.get('lastViewedAt'),
        'view_offset': item.attrib.get('viewOffset'),
        'user_rating': item.attrib.get('userRating'),
        'file_path': None
    }

    meta = get_metadata(data['rating_key'])
    data['file_path'] = extract_file_path(meta)

    cur.execute('''
        INSERT OR REPLACE INTO media 
        (rating_key, title, library_section, guid, file_path, duration, view_count, last_viewed_at, view_offset, user_rating)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['rating_key'], data['title'], data['library_section'], data['guid'], data['file_path'],
        data['duration'], data['view_count'], data['last_viewed_at'], data['view_offset'], data['user_rating']
    ))
    conn.commit()

if __name__ == '__main__':
    export_plex_library()
