import os
import sys
import json
import time
import datetime
import urllib.request
import urllib.error

def main():
    # Allow running with a different username from command line, defaulting to darkkkkkkk0
    username = sys.argv[1] if len(sys.argv) > 1 else "darkkkkkkk0"
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pgn_filename = os.path.join(script_dir, f"{username}_games.pgn")
    uuids_filename = os.path.join(script_dir, f"{username}_uuids.txt")
    processed_archives_filename = os.path.join(script_dir, f"{username}_processed_archives.txt")


    # Load already downloaded game UUIDs
    downloaded_uuids = set()
    if os.path.exists(uuids_filename):
        with open(uuids_filename, "r", encoding="utf-8") as f:
            downloaded_uuids = {line.strip() for line in f if line.strip()}

    # Load already completed archive URLs
    processed_archives = set()
    if os.path.exists(processed_archives_filename):
        with open(processed_archives_filename, "r", encoding="utf-8") as f:
            processed_archives = {line.strip() for line in f if line.strip()}

    print(f"Loaded {len(downloaded_uuids)} already downloaded games.")
    print(f"Loaded {len(processed_archives)} already completed monthly archives.")

    # Fetch list of archives
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    print(f"Fetching archive list from {archives_url}...")
    
    headers = {
        "User-Agent": "ChessDownloader/1.0 (contact: chess_downloader_script@example.com)"
    }
    
    req = urllib.request.Request(archives_url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            archive_urls = data.get("archives", [])
    except urllib.error.HTTPError as e:
        print(f"Error fetching archives list: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

    print(f"Found {len(archive_urls)} total monthly archives.")

    current_month_suffix = datetime.datetime.now().strftime("%Y/%m")
    new_games_count = 0
    
    # Open files in append mode
    with open(pgn_filename, "a", encoding="utf-8") as f_pgn, \
         open(uuids_filename, "a", encoding="utf-8") as f_uuids:
         
        for archive_url in archive_urls:
            if archive_url in processed_archives:
                continue
                
            print(f"Fetching games from {archive_url}...")
            time.sleep(0.3)  # Small delay to respect Chess.com rate limit
            
            req = urllib.request.Request(archive_url, headers=headers)
            try:
                with urllib.request.urlopen(req) as response:
                    archive_data = json.loads(response.read().decode("utf-8"))
                    games = archive_data.get("games", [])
            except urllib.error.HTTPError as e:
                print(f"Error fetching archive {archive_url}: {e}. Skipping this month for now.")
                continue
            except Exception as e:
                print(f"Unexpected error for {archive_url}: {e}. Skipping this month for now.")
                continue
                
            archive_new_games = 0
            for game in games:
                uuid = game.get("uuid")
                if not uuid:
                    continue
                if uuid in downloaded_uuids:
                    continue
                    
                pgn_content = game.get("pgn")
                if not pgn_content:
                    continue
                    
                # Clean up and append PGN content
                pgn_content = pgn_content.strip()
                f_pgn.write(pgn_content + "\n\n")
                
                # Track uuid to prevent duplicate downloads
                downloaded_uuids.add(uuid)
                f_uuids.write(uuid + "\n")
                
                archive_new_games += 1
                new_games_count += 1
                
            print(f"-> Processed {len(games)} games: saved {archive_new_games} new games.")
            
            # If the archive is not the current month, mark it as completed so we never fetch it again
            if current_month_suffix not in archive_url:
                processed_archives.add(archive_url)
                with open(processed_archives_filename, "a", encoding="utf-8") as f_arch:
                    f_arch.write(archive_url + "\n")
                    
    print(f"\nDone! Downloaded {new_games_count} new games.")
    print(f"Total games now stored: {len(downloaded_uuids)}")

if __name__ == "__main__":
    main()
