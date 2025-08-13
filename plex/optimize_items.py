import os
import logging
from datetime import datetime
from plexapi.server import PlexServer
from plexapi.exceptions import BadRequest

# Environment variables
PLEX_URL = os.environ.get("PLEX_URL")
PLEX_TOKEN = os.environ.get("PLEX_TOKEN")

# Constants
LIBRARY_NAMES = ["My Movies", "My TV Shows", "YouTube"]
MAX_ITEMS_TO_OPTIMIZE = 10
OPTIMIZATION_TARGET = "Mobile"

# Logging
logfile_path = os.path.join(os.path.dirname(__file__), "optimize_items.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(logfile_path, mode='w'),
        logging.StreamHandler()
    ]
)

def get_plex_server():
    return PlexServer(PLEX_URL, PLEX_TOKEN)

def has_mobile_optimized_versions(item):
    try:
        return [
            media for media in item.media
            if media.optimizedForStreaming and media.title and (
                OPTIMIZATION_TARGET.lower() in media.title.lower()
                or "mobile" in media.title.lower()
            )
        ]
    except Exception as e:
        logging.warning(f"Could not inspect media for '{item.title}': {e}")
        return []

def get_sort_key(item):
    return getattr(item, 'originallyAvailableAt', None) or getattr(item, 'addedAt', None) or datetime.now()

def collect_items_to_optimize(plex):
    items_to_optimize = []

    for library_name in LIBRARY_NAMES:
        try:
            section = plex.library.section(library_name)
        except Exception as e:
            logging.warning(f"Could not access section '{library_name}': {e}")
            continue

        try:
            if section.type == "movie":
                items = section.search(unwatched=True)
            elif section.type == "show":
                items = []
                for show in section.all():
                    try:
                        episodes = show.episodes(unwatched=True)
                        items.extend(episodes)
                    except Exception as e:
                        logging.warning(f"Could not get episodes for show '{show.title}': {e}")
            else:
                continue
        except Exception as e:
            logging.warning(f"Failed to retrieve items for section '{library_name}': {e}")
            continue

        sorted_items = sorted(items, key=get_sort_key)

        for item in sorted_items:
            if len(items_to_optimize) >= MAX_ITEMS_TO_OPTIMIZE:
                return items_to_optimize
            items_to_optimize.append(item)

    return items_to_optimize

def optimize_items(items):
    for item in items:
        try:
            item.optimize(target=OPTIMIZATION_TARGET)
            logging.info(f"Created optimized version for: {item.title}")
        except BadRequest as e:
            if "The media version already exists" in str(e):
                logging.warning(f"Optimization already exists for: {item.title}")
            else:
                logging.error(f"Failed to optimize '{item.title}': {e}")
        except Exception as e:
            logging.error(f"Failed to optimize '{item.title}': {e}")

def cleanup_optimized_versions(plex):
    for library_name in LIBRARY_NAMES:
        try:
            section = plex.library.section(library_name)
        except Exception as e:
            logging.warning(f"Could not access section '{library_name}' for cleanup: {e}")
            continue

        try:
            if section.type == "movie":
                items = section.search()
            elif section.type == "show":
                items = []
                for show in section.all():
                    try:
                        episodes = show.episodes()
                        items.extend(episodes)
                    except Exception as e:
                        logging.warning(f"Could not get episodes for show '{show.title}': {e}")
            else:
                continue
        except Exception as e:
            logging.warning(f"Failed to retrieve items for cleanup in section '{library_name}': {e}")
            continue

        for item in items:
            try:
                if item.isWatched:
                    for version in has_mobile_optimized_versions(item):
                        version.delete()
                        logging.info(f"Deleted optimized version for: {item.title}")
            except Exception as e:
                logging.warning(f"Failed to cleanup optimized version for '{item.title}': {e}")

def main():
    logging.info("Script started: optimize_items.py")
    plex = get_plex_server()
    items_to_optimize = collect_items_to_optimize(plex)
    optimize_items(items_to_optimize)
    cleanup_optimized_versions(plex)

if __name__ == "__main__":
    main()
