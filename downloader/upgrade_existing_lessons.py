import os
import re
import json
import glob

def add_coordinates_to_board(board_html):
    # Find all squares
    # Format matches <div class="square light" data-square="h1">...</div>
    square_pattern = re.compile(r'(<div class="square ([a-z]+)" data-square="([a-h][1-8])">)(.*?)</div>', re.DOTALL)
    squares = square_pattern.findall(board_html)
    if not squares:
        return board_html
        
    first_square_name = squares[0][2]  # e.g., "a8" or "h1"
    is_white = first_square_name == "a8"
    
    def replace_square(match):
        start_tag = match.group(1)
        sq_class = match.group(2)
        sq_name = match.group(3)
        inner_content = match.group(4)
        
        file_letter = sq_name[0]
        rank_num = sq_name[1]
        
        col = ord(file_letter) - ord('a')
        row = int(rank_num) - 1
        
        show_rank = (col == 0) if is_white else (col == 7)
        show_file = (row == 0) if is_white else (row == 7)
        
        coord_html = ""
        if show_rank:
            coord_html += f'<span class="coord coord-rank">{rank_num}</span>'
        if show_file:
            coord_html += f'<span class="coord coord-file">{file_letter}</span>'
            
        # Strip existing coordinate spans if any
        inner_content = re.sub(r'<span class="coord[^"]*">.*?</span>', '', inner_content)
        
        return f'{start_tag}{coord_html}{inner_content}</div>'
        
    return square_pattern.sub(replace_square, board_html)

def upgrade_lesson_file(filepath):
    filename = os.path.basename(filepath)
    num_match = re.match(r'^(\d+)', filename)
    lesson_num = int(num_match.group(1)) if num_match else 1
    
    print(f"Upgrading {filename}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Try to parse existing metadata first
    existing_meta = None
    meta_match = re.search(r'<!-- LESSON_METADATA:\s*({.*?})\s*-->', content)
    if meta_match:
        try:
            existing_meta = json.loads(meta_match.group(1))
        except:
            pass
            
    # Extract stats to create metadata block (fallback if not parsed)
    wins = 0
    losses = 0
    rating = 300
    
    if existing_meta:
        wins = existing_meta.get("wins", 0)
        losses = existing_meta.get("losses", 0)
        rating = existing_meta.get("rating", 300)
    else:
        wins_match = re.search(r'<div class="stat-val win-stat">(\d+)</div>', content)
        wins = int(wins_match.group(1)) if wins_match else 0
        
        losses_match = re.search(r'<div class="stat-val"[^>]*>(\d+)</div>\s*<div class="stat-label">Losses</div>', content)
        losses = int(losses_match.group(1)) if losses_match else 0
        
        rating_match = re.search(r'<div class="stat-val"[^>]*>(\d+)</div>\s*<div class="stat-label">Current Rating</div>', content)
        rating = int(rating_match.group(1)) if rating_match else 300
        
    # Hardcoded original stats mapping fallback for Lesson 1 and Lesson 2
    original_stats = {
        1: {"wins": 254, "losses": 269, "rating": 347},
        2: {"wins": 12, "losses": 8, "rating": 347}
    }
    if wins == 0 and losses == 0 and rating == 300:
        if lesson_num in original_stats:
            wins = original_stats[lesson_num]["wins"]
            losses = original_stats[lesson_num]["losses"]
            rating = original_stats[lesson_num]["rating"]
            
    challenges = len(re.findall(r'class="chess-board"', content))
    
    # 1. Construct metadata block
    metadata_block = f'<!-- LESSON_METADATA: {{"num": {lesson_num}, "wins": {wins}, "losses": {losses}, "rating": {rating}, "challenges": {challenges}}} -->'
    
    # Find all puzzle cards on the page
    puzzle_pattern = re.compile(r'<!-- Puzzle \d+ -->.*?<div class="card">.*?</div>\s*(?=<!-- Puzzle|<!-- General|\Z)', re.DOTALL)
    puzzle_blocks = puzzle_pattern.findall(content)
    
    if not puzzle_blocks:
        print(f"Warning: No puzzle cards found in {filename} via regex. Trying fallback splitter.")
        # Fallback splitter
        parts = re.split(r'(<!-- Puzzle \d+ -->)', content)
        puzzle_blocks = []
        for i in range(1, len(parts), 2):
            comment = parts[i]
            body = parts[i+1]
            # Extract card
            card_match = re.search(r'<div class="card">.*?</div>', body, re.DOTALL)
            if card_match:
                puzzle_blocks.append(f"{comment}\n{card_match.group(0)}")
                
    # Update coordinates inside puzzle boards and strip instruction texts
    updated_puzzles = []
    for pb in puzzle_blocks:
        pb_clean = re.sub(r'<p>Find the (winning|safest) move\.\s*Click 👁️ to preview\.</p>\s*', '', pb)
        pb_clean = re.sub(r'<p>What was the strongest tactical option here\?.*?</p>\s*', '', pb_clean)
        pb_clean = re.sub(r'<p>What is a safer, solid choice here\?.*?</p>\s*', '', pb_clean)
        updated_puzzles.append(add_coordinates_to_board(pb_clean))
        
    puzzles_html = "\n\n".join(updated_puzzles)
    
    # Extract player name (usually from footer)
    player_match = re.search(r'Chess Mastery Journey for (.*?) •', content)
    player_name = player_match.group(1).strip() if player_match else "darkkkkkkk0"
    
    # 2. Build the upgraded lesson HTML content
    upgraded_html = f"""{metadata_block}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lesson {lesson_num}: Personalized Game Review</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Plus+Jakarta+Sans:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --accent-primary: #8b5cf6;
            --accent-secondary: #ec4899;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --success: #10b981;
            --danger: #ef4444;
            --board-light: #f0d9b5;
            --board-dark: #b58863;
        }}

        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }}

        .app-header {{
            background: linear-gradient(135deg, #1e1b4b, #1d4ed8);
            padding: 0.8rem 1.5rem;
            border-bottom: 3px solid var(--accent-primary);
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }}

        .header-content {{
            max-width: 900px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.8rem;
        }}

        .back-link {{
            color: #60a5fa;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 0.25rem;
            transition: color 0.2s ease;
        }}

        .back-link:hover {{
            color: var(--accent-primary);
        }}

        .header-title-section h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.3rem;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(to right, #60a5fa, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        main {{
            max-width: 900px;
            margin: 2rem auto;
            padding: 0 1rem;
        }}

        .card {{
            background-color: var(--card-bg);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}

        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 15px 30px -5px rgba(59, 130, 246, 0.1);
        }}

        h2 {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.6rem;
            font-weight: 700;
            margin-top: 0;
            color: #e2e8f0;
            border-left: 5px solid var(--accent-primary);
            padding-left: 0.75rem;
        }}

        .chess-grid-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 1.5rem;
            align-items: center;
            margin: 1rem 0;
        }}

        .chess-board {{
            display: grid;
            grid-template-columns: repeat(8, 1fr);
            grid-template-rows: repeat(8, 1fr);
            width: 100%;
            max-width: 320px;
            aspect-ratio: 1;
            border: 6px solid #334155;
            border-radius: 8px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
            user-select: none;
            margin: 0 auto;
        }}

        .square {{
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 1.8rem;
            font-family: 'Segoe UI Symbol', sans-serif;
            position: relative;
            aspect-ratio: 1;
        }}

        .coord {{
            position: absolute;
            font-weight: 800;
            font-size: 0.6rem;
            line-height: 1;
            user-select: none;
            pointer-events: none;
            font-family: 'Outfit', sans-serif;
        }}
        .coord-rank {{
            top: 2px;
            left: 3px;
        }}
        .coord-file {{
            bottom: 2px;
            right: 3px;
        }}
        .square.light .coord {{
            color: var(--board-dark);
        }}
        .square.dark .coord {{
            color: var(--board-light);
        }}

        .square.threat-source {{
            background-color: rgba(239, 68, 68, 0.7) !important;
            box-shadow: inset 0 0 12px #ef4444;
            transition: background-color 0.2s ease;
        }}

        .square.threat-target {{
            background-color: rgba(239, 68, 68, 0.4) !important;
            box-shadow: inset 0 0 10px #ef4444;
            border: 2px dashed #ef4444 !important;
            transition: background-color 0.2s ease;
        }}

        .preview-btn {{
            background: var(--card-bg);
            border: 2px solid #334155;
            padding: 0.6rem;
            border-radius: 8px;
            cursor: pointer;
            color: white;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .preview-btn:hover {{
            border-color: var(--accent-primary);
        }}

        .preview-btn.preview-active {{
            background: var(--accent-primary) !important;
            border-color: var(--accent-primary) !important;
            box-shadow: 0 0 10px rgba(139, 92, 246, 0.4);
        }}

        .square.light {{
            background-color: var(--board-light);
        }}

        .square.dark {{
            background-color: var(--board-dark);
        }}

        .square.highlighted::after {{
            content: '';
            width: 15px;
            height: 15px;
            border-radius: 50%;
            background: rgba(139, 92, 246, 0.6);
            position: absolute;
            z-index: 5;
        }}

        .piece {{
            display: inline-block;
            line-height: 1;
            z-index: 2;
        }}
        .piece.white {{
            color: #ffffff;
            filter: drop-shadow(0 0 1.5px #000) drop-shadow(0 0 2.5px #000);
        }}
        .piece.black {{
            color: #1a1a1a;
            filter: drop-shadow(0 0 1.5px #fff) drop-shadow(0 0 2.5px #fff);
        }}

        .explanation-side {{
            flex: 1;
            min-width: 280px;
        }}

        .quiz-container {{
            background: rgba(15, 23, 42, 0.6);
            border-radius: 12px;
            padding: 1rem;
            margin-top: 1rem;
        }}

        .quiz-option {{
            background: var(--card-bg);
            border: 2px solid #334155;
            padding: 0.6rem 0.8rem;
            border-radius: 8px;
            margin-bottom: 0;
            cursor: pointer;
            transition: all 0.2s ease;
            font-weight: 600;
            font-size: 0.95rem;
        }}

        .quiz-option:hover {{
            border-color: var(--accent-primary);
            background: rgba(139, 92, 246, 0.05);
        }}

        .quiz-option.correct {{
            border-color: var(--success);
            background: rgba(16, 185, 129, 0.1);
            color: #a7f3d0;
        }}

        .quiz-option.incorrect {{
            border-color: var(--danger);
            background: rgba(239, 68, 68, 0.1);
            color: #fca5a5;
        }}

        .feedback-msg {{
            font-weight: 700;
            margin-top: 1rem;
            padding: 0.75rem;
            border-radius: 6px;
            display: none;
            font-size: 0.95rem;
        }}

        .feedback-msg.success {{
            background: rgba(16, 185, 129, 0.1);
            color: var(--success);
            border-left: 4px solid var(--success);
        }}

        .feedback-msg.danger {{
            background: rgba(239, 68, 68, 0.1);
            color: var(--danger);
            border-left: 4px solid var(--danger);
        }}

        .badge {{
            background: var(--accent-primary);
            color: #fff;
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05rem;
            display: inline-block;
            margin-bottom: 0.5rem;
        }}

        footer {{
            text-align: center;
            padding: 2rem 0;
            color: var(--text-muted);
            font-size: 0.9rem;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            margin-top: 3rem;
        }}

        @media (max-width: 600px) {{
            main {{
                margin: 1rem auto;
                padding: 0 0.5rem;
            }}
            .card {{
                padding: 1.25rem;
                border-radius: 12px;
                margin-bottom: 1.25rem;
            }}
            h2 {{
                font-size: 1.3rem;
            }}
            .chess-board {{
                max-width: 100%;
                border-width: 4px;
            }}
            .square {{
                font-size: 1.5rem;
            }}
            .square.highlighted::after {{
                width: 10px;
                height: 10px;
            }}
            .quiz-option {{
                padding: 0.5rem 0.7rem;
                font-size: 0.9rem;
            }}
            .preview-btn {{
                padding: 0.5rem;
            }}
        }}
    </style>
</head>
<body>

    <header class="app-header">
        <div class="header-content">
            <a href="../index.html" class="back-link">
                <span>←</span> Dashboard
            </a>
            <div class="header-title-section">
                <h1>Lesson {lesson_num}: Personalized Game Review</h1>
            </div>
            <div class="header-stats-tag">
                <span class="badge">Lesson {lesson_num}</span>
            </div>
        </div>
    </header>

    <main>
        {puzzles_html}
    </main>

    <footer>
        <p>Chess Mastery Journey for {player_name} • Made with 💙</p>
    </footer>

    <script>
        const baseBoardStates = {{}};
        const activeMoves = {{}};
        
        window.addEventListener('load', () => {{
            const boards = document.querySelectorAll('.chess-board');
            boards.forEach(board => {{
                baseBoardStates[board.id] = board.innerHTML;
            }});
        }});
        
        function applyMoveToBoard(board, fromSq, toSq) {{
            const fromEl = board.querySelector(`[data-square="${{fromSq}}"]`);
            const toEl = board.querySelector(`[data-square="${{toSq}}"]`);
            if (!fromEl || !toEl) return;
            
            const piece = fromEl.innerHTML;
            fromEl.innerHTML = '';
            toEl.innerHTML = piece;
            fromEl.style.backgroundColor = 'rgba(139, 92, 246, 0.4)';
            toEl.style.backgroundColor = 'rgba(139, 92, 246, 0.4)';
        }}

        const activePreviews = {{}};

        function togglePreview(btn, puzzleId, fromSq, toSq) {{
            const board = document.getElementById('board-' + puzzleId);
            if (!board) return;

            const container = board.closest('.card');
            const buttons = container.querySelectorAll('.preview-btn');

            if (activePreviews[puzzleId] === btn) {{
                delete activePreviews[puzzleId];
                btn.classList.remove('preview-active');
                
                board.innerHTML = baseBoardStates[board.id];
                board.querySelectorAll('.square').forEach(sq => {{
                    sq.classList.remove('threat-source', 'threat-target');
                }});
                
                const active = activeMoves[puzzleId];
                if (active) {{
                    applyMoveToBoard(board, active.fromSq, active.toSq);
                    if (active.type === 'blunder' && active.refutationFrom && active.refutationTo) {{
                        const fromEl = board.querySelector(`[data-square="${{active.refutationFrom}}"]`);
                        const toEl = board.querySelector(`[data-square="${{active.refutationTo}}"]`);
                        if (fromEl) fromEl.classList.add('threat-source');
                        if (toEl) toEl.classList.add('threat-target');
                    }}
                }}
                return;
            }}

            buttons.forEach(b => b.classList.remove('preview-active'));
            btn.classList.add('preview-active');
            activePreviews[puzzleId] = btn;

            board.innerHTML = baseBoardStates[board.id];
            board.querySelectorAll('.square').forEach(sq => {{
                sq.classList.remove('threat-source', 'threat-target');
            }});

            applyMoveToBoard(board, fromSq, toSq);
        }}

        function checkPuzzle(puzzleId, type, optionIdx, fromSq, toSq, refutationFrom, refutationTo) {{
            activeMoves[puzzleId] = {{ fromSq, toSq, refutationFrom, refutationTo, type }};
            
            const board = document.getElementById('board-' + puzzleId);
            if (!board) return;
            
            delete activePreviews[puzzleId];
            const container = board.closest('.card');
            const buttons = container.querySelectorAll('.preview-btn');
            buttons.forEach(b => b.classList.remove('preview-active'));
            
            board.innerHTML = baseBoardStates[board.id];
            board.querySelectorAll('.square').forEach(sq => {{
                sq.classList.remove('threat-source', 'threat-target');
            }});
            
            applyMoveToBoard(board, fromSq, toSq);
            
            const feedback = document.getElementById('p' + puzzleId + '-feedback');
            feedback.style.display = 'block';
            
            for (let i = 1; i <= 3; i++) {{
                const opt = document.getElementById('p' + puzzleId + '-o' + i);
                if (opt) opt.className = 'quiz-option';
            }}
            
            const clickedOpt = document.getElementById('p' + puzzleId + '-o' + optionIdx);
            const feedbackText = clickedOpt ? clickedOpt.getAttribute('data-feedback') : '';
            if (type === 'blunder') {{
                if (clickedOpt) clickedOpt.className = 'quiz-option incorrect';
                feedback.className = 'feedback-msg danger';
                feedback.innerHTML = feedbackText;
                
                if (refutationFrom && refutationTo) {{
                    const fromEl = board.querySelector(`[data-square="${{refutationFrom}}"]`);
                    const toEl = board.querySelector(`[data-square="${{refutationTo}}"]`);
                    if (fromEl) fromEl.classList.add('threat-source');
                    if (toEl) toEl.classList.add('threat-target');
                }}
            }} else if (type === 'correct') {{
                if (clickedOpt) clickedOpt.className = 'quiz-option correct';
                feedback.className = 'feedback-msg success';
                feedback.innerHTML = feedbackText;
            }}
        }}
    </script>
</body>
</html>
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(upgraded_html)
        
    print(f"Successfully upgraded {filename}!")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    lessons_dir = os.path.join(project_root, "lessons")
    
    lesson_files = glob.glob(os.path.join(lessons_dir, "*.html"))
    for filepath in lesson_files:
        try:
            upgrade_lesson_file(filepath)
        except Exception as e:
            print(f"Error upgrading {filepath}: {e}")

if __name__ == "__main__":
    main()
