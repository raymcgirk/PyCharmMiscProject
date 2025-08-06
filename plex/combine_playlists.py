import os
import sys
import time

import requests
from plexapi.exceptions import NotFound
from plexapi.server import PlexServer

import logging

# Set up logging to a file in the same directory as the script
script_dir = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(script_dir, "combine_playlists.log")

logging.basicConfig(
    filename=log_path,
    filemode='w',
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Also output to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.getLogger().addHandler(console_handler)

logging.info("Script started")

PLEX_URL = os.getenv("PLEX_URL", "http://localhost:32400")
PLEX_TOKEN = os.getenv("PLEX_TOKEN", "")

# Retry logic for unstable network/API
def safe_get_section(plex_server, section_name, retries=3, delay=10):
    for attempt_index in range(retries):
        try:
            return plex_server.library.section(section_name)
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as error:
            logging.warning(f"Timeout/connection error on section '{section_name}', attempt {attempt_index + 1}/{retries}: {error}")
            time.sleep(delay)
        except NotFound:
            logging.warning(f"Library section '{section_name}' not found.")
            break
    raise RuntimeError(f"Failed to get section '{section_name}' after {retries} attempts")

# Connect to Plex server with retry
for attempt in range(3):
    try:
        plex = PlexServer(PLEX_URL, PLEX_TOKEN)
        break
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to connect to Plex server (attempt {attempt + 1}/3): {e}")
        time.sleep(10)
else:
    logging.error("Could not connect to Plex server after retries.")
    raise RuntimeError("Could not connect to Plex server after retries.")

# Safely fetch sections
movies_section = safe_get_section(plex, 'My Movies')
tv_shows_section = safe_get_section(plex, 'My TV Shows')
try:
    youtube_section = safe_get_section(plex, 'YouTube')
except RuntimeError:
    youtube_section = None
    logging.warning("YouTube library section not found or unavailable. Skipping...")

# Fetch all unique years in the library
years = set()

# Get all movie years
for movie in movies_section.all():
    if movie.originallyAvailableAt:
        years.add(movie.originallyAvailableAt.year)

# Get all TV show years
for show in tv_shows_section.all():
    if show.originallyAvailableAt:
        years.add(show.originallyAvailableAt.year)

# Get all YouTube video years
if youtube_section:
    for video in youtube_section.all():
        if video.originallyAvailableAt:
            years.add(video.originallyAvailableAt.year)

# If no years are found, exit
if not years:
    logging.info("No valid content years found.")
    sys.exit(0)

# Determine the range of decades
min_year = min(years)
max_year = max(years)

# Generate decade ranges dynamically
decades = [
    {"name": f"{start_year}s", "years": range(start_year, start_year + 10)}
    for start_year in range(min_year - (min_year % 10), max_year + 10, 10)
]

# Process each decade
for decade in decades:
    try:
        combined_items = []

        # Search for unwatched movies and TV episodes year by year and combine results
        for year in decade['years']:
            # Unwatched movies
            unwatched_movies = movies_section.search(unwatched=True, year=year)
            # Unwatched TV episodes
            unwatched_tv_episodes = tv_shows_section.searchEpisodes(unwatched=True, year=year)
            # Unwatched YouTube videos
            unwatched_youtube = []
            if youtube_section:
                try:
                    unwatched_youtube = youtube_section.search(unwatched=True, year=year)
                except Exception as e:
                    logging.error(f"Error searching YouTube videos for year {year}: {e}")

            # Add movies and TV episodes to the combined list
            combined_items += unwatched_movies + unwatched_tv_episodes + unwatched_youtube

        # Print summary
        logging.info(f"Found {len(combined_items)} unwatched items for {decade['name']}")

        # Only create/update a playlist if there are items
        if combined_items:
            combined_items.sort(key=lambda x: x.originallyAvailableAt or x.addedAt)
            combined_playlist_name = f"{decade['name']} Unwatched Combined"

            try:
                combined_playlist = plex.playlist(combined_playlist_name)
                logging.info(f"Updating existing playlist '{combined_playlist_name}'")

                current_items = combined_playlist.items()
                items_to_add = [item for item in combined_items if item not in current_items]
                items_to_remove = [item for item in current_items if item not in combined_items]

                # Remove items not in current combined list
                if items_to_remove:
                    combined_playlist.removeItems(items_to_remove)
                    logging.info(f"Removed {len(items_to_remove)} items from '{combined_playlist_name}'")

                # Add items in batches of 500
                for i in range(0, len(items_to_add), 500):
                    batch = items_to_add[i:i + 500]
                    combined_playlist.addItems(batch)
                    logging.info(f"Added batch {i // 500 + 1} with {len(batch)} items to '{combined_playlist_name}'")
                    time.sleep(1)

            except NotFound:
                # Create playlist in 500-item batches
                logging.info(f"Creating new playlist '{combined_playlist_name}'")

                combined_playlist = None

                for i in range(0, len(combined_items), 500):
                    batch = combined_items[i:i + 500]
                    if i == 0:
                        combined_playlist = plex.createPlaylist(title=combined_playlist_name, items=batch)
                        logging.info(f"Created playlist '{combined_playlist_name}' with initial {len(batch)} items")
                    else:
                        combined_playlist.addItems(batch)
                        logging.info(
                            f"Appended batch {i // 500 + 1} with {len(batch)} items to '{combined_playlist_name}'")
                    time.sleep(1)

            except Exception as playlist_error:
                logging.error(f"Failed to access or create playlist '{combined_playlist_name}': {playlist_error}")
                raise

    except Exception as decade_error:
        logging.error(f"Failed to combine playlists for {decade['name']}: {decade_error}")