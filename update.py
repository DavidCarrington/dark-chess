import subprocess
import sys
import os

def run_script(script_name, args=[]):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, "downloader", script_name)
    cmd = [sys.executable, script_path] + args
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"Error running {script_name}")
        return False
    return True

def main():
    username = sys.argv[1] if len(sys.argv) > 1 else "darkkkkkkk0"
    extra_args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    # Check if the first argument itself is a flag (e.g. force) rather than a username
    if username.startswith("-") or username == "force":
        extra_args = [username] + extra_args
        username = "darkkkkkkk0"
    
    print("=" * 60)
    print("STARTING CHESS GAME FETCH & BLUNDER ANALYSIS LOOP")
    print("=" * 60)
    
    print("\n[STEP 1] Fetching new matches from Chess.com...")
    if not run_script("download_games.py", [username]):
        sys.exit(1)
        
    print("\n[STEP 2] Running blunder scan on last 20 games...")
    if not run_script("analyze_recent_games.py", [username] + extra_args):
        sys.exit(1)
        
    print("\n[STEP 3] Rebuilding the Dashboard Index...")
    if not run_script("generate_index.py"):
        sys.exit(1)
        
    # Paths for display
    script_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(script_dir, "index.html")
    
    print("\n" + "=" * 60)
    print("SUCCESS: Dynamic Lessons and Dashboard Rebuilt!")
    print("=" * 60)
    print(f"Interactive dashboard available at:\nfile:///{index_path.replace(os.sep, '/')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
