import chess
import chess.pgn
import os
import sys
import json

def get_material(board, color):
    values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
    return sum(values.get(p.piece_type, 0) for p in board.piece_map().values() if p.color == color)

def evaluate_move_threat(board, move, player_color):
    temp_board = board.copy()
    temp_board.push(move)
    opponent_color = not player_color
    max_diff = 0
    worst_op_move = None
    piece_lost_type = None
    
    for op_move in temp_board.legal_moves:
        if temp_board.is_capture(op_move):
            cap_board = temp_board.copy()
            cap_board.push(op_move)
            val_before = get_material(temp_board, player_color)
            val_after = get_material(cap_board, player_color)
            diff = val_before - val_after
            if diff > max_diff:
                max_diff = diff
                worst_op_move = op_move
                target_piece = temp_board.piece_at(op_move.to_square)
                piece_lost_type = target_piece.piece_type if target_piece else chess.PAWN

    if worst_op_move:
        piece_name = chess.piece_name(piece_lost_type).capitalize()
        return max_diff, temp_board.san(worst_op_move), piece_name, worst_op_move
    return 0, None, None, None

def find_safe_move(board, player_color):
    legal_moves = list(board.legal_moves)
    safe_moves = []
    
    # Check each legal move
    for move in legal_moves:
        max_diff, _, _, _ = evaluate_move_threat(board, move, player_color)
        
        # If no immediate material loss, it is a safe move
        if max_diff == 0:
            safe_moves.append(move)
            
    if safe_moves:
        # Prioritize castles, major/minor piece development, pawn pushes
        for m in safe_moves:
            san = board.san(m)
            if "O-O" in san or san.startswith(("N", "B", "d", "e")):
                return m, san
        return safe_moves[0], board.san(safe_moves[0])
    return None, None

def board_to_html_grid(board, player_color):
    # Map Unicode pieces - use solid pieces for both colors styled via CSS for best contrast
    piece_symbols = {
        'P': '♟', 'N': '♞', 'B': '♝', 'R': '♜', 'Q': '♛', 'K': '♚',
        'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
    }
    
    is_white = player_color == chess.WHITE
    rows = range(7, -1, -1) if is_white else range(8)
    cols = range(8) if is_white else range(7, -1, -1)
    
    html = []
    for row in rows:
        for col in cols:
            square = chess.square(col, row)
            piece = board.piece_at(square)
            if piece:
                symbol = piece_symbols.get(piece.symbol(), "")
                color_class = "white" if piece.color == chess.WHITE else "black"
                symbol_html = f'<span class="piece {color_class}">{symbol}</span>'
            else:
                symbol_html = ""
            is_light = (row + col) % 2 != 0
            square_class = "light" if is_light else "dark"
            square_name = chess.square_name(square)
            html.append(f'<div class="square {square_class}" data-square="{square_name}">{symbol_html}</div>')
    return "\n".join(html)

def main():
    player_name = sys.argv[1] if len(sys.argv) > 1 else "darkkkkkkk0"
    player_name_lower = player_name.lower()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pgn_path = os.path.join(script_dir, f"{player_name}_games.pgn")
    last_count_path = os.path.join(script_dir, "last_analysis_count.txt")
    
    if not os.path.exists(pgn_path):
        print(f"Error: {pgn_path} not found. Run download_games.py first.")
        sys.exit(1)
        
    print(f"Reading games from {pgn_path}...")
    games = []
    with open(pgn_path, "r", encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            games.append(game)
            
    total_games_stored = len(games)
    
    # Load previous total game count
    prev_total = 0
    if os.path.exists(last_count_path):
        try:
            with open(last_count_path, "r") as lf:
                prev_total = int(lf.read().strip())
        except:
            prev_total = 0
            
    new_matches_count = max(0, total_games_stored - prev_total)
    
    # Save current total
    with open(last_count_path, "w") as lf:
        lf.write(str(total_games_stored))
        
    last_20 = games[-20:]
    print(f"Analyzing the last {len(last_20)} games played by {player_name}...")
    
    # Extract ratings for the graph (last 30 games)
    rating_history = []
    for game in games[-30:]:
        headers = game.headers
        is_white = headers.get("White", "").lower() == player_name_lower
        is_black = headers.get("Black", "").lower() == player_name_lower
        rating_str = headers.get("WhiteElo", "") if is_white else headers.get("BlackElo", "")
        if rating_str.isdigit():
            rating_history.append(int(rating_str))
            
    # Default rating history if empty
    if not rating_history:
        rating_history = [300]
        
    wins = 0
    losses = 0
    draws = 0
    blunder_details = []
    
    queen_blunders = 0
    rook_blunders = 0
    minor_blunders = 0
    
    for g_idx, game in enumerate(last_20, 1):
        headers = game.headers
        white = headers.get("White", "")
        black = headers.get("Black", "")
        is_white = white.lower() == player_name_lower
        player_color = chess.WHITE if is_white else chess.BLACK
        opponent_color = chess.BLACK if is_white else chess.WHITE
        opponent = black if is_white else white
        date = headers.get("Date", "Unknown Date")
        result = headers.get("Result", "*")
        game_url = headers.get("Link", headers.get("url", ""))
        
        if result == "1-0":
            if is_white: wins += 1
            else: losses += 1
        elif result == "0-1":
            if not is_white: wins += 1
            else: losses += 1
        elif result in ["1/2-1/2", "1/2"]:
            draws += 1
            
        board = game.board()
        moves = list(game.mainline_moves())
        boards = [board.copy()]
        move_sans = []
        for m in moves:
            move_sans.append(board.san(m))
            board.push(m)
            boards.append(board.copy())
            
        start_idx = 0 if is_white else 1
        for i in range(start_idx, len(moves) - 1, 2):
            player_move_idx = i
            opponent_move_idx = i + 1
            
            board_before = boards[player_move_idx]
            board_after_opponent = boards[opponent_move_idx + 1]
            
            mat_before = get_material(board_before, player_color) - get_material(board_before, opponent_color)
            mat_after = get_material(board_after_opponent, player_color) - get_material(board_after_opponent, opponent_color)
            
            net_change = mat_after - mat_before
            
            if net_change <= -2:
                # Check for sacrifices/trades: look one ply ahead at the player's recapture
                if opponent_move_idx + 1 < len(moves):
                    board_after_recapture = boards[opponent_move_idx + 2]
                    mat_after_recapture = get_material(board_after_recapture, player_color) - get_material(board_after_recapture, opponent_color)
                    resolved_net_change = mat_after_recapture - mat_before
                    if resolved_net_change > -2:
                        continue # It was a planned sacrifice or trade! Not a blunder.
                blunder_move = moves[player_move_idx]
                
                piece_type = board_before.piece_at(blunder_move.from_square).piece_type if board_before.piece_at(blunder_move.from_square) else chess.PAWN
                piece_name = chess.piece_name(piece_type).capitalize()
                
                if net_change <= -7: queen_blunders += 1
                elif net_change <= -4: rook_blunders += 1
                else: minor_blunders += 1
                
                safe_move_obj, safe_move_san = find_safe_move(board_before, player_color)
                
                import random
                # Find an alternative plausible move
                legal_moves = list(board_before.legal_moves)
                alt_move_objs = [m for m in legal_moves if m != blunder_move and (not safe_move_obj or m != safe_move_obj)]
                random_move_obj = random.choice(alt_move_objs) if alt_move_objs else blunder_move
                random_move_san = board_before.san(random_move_obj)
                
                diff, op_san, piece_lost, op_move_obj = evaluate_move_threat(board_before, random_move_obj, player_color)
                if diff > 0 and op_move_obj:
                    random_refutation_from = chess.square_name(op_move_obj.from_square)
                    random_refutation_to = chess.square_name(op_move_obj.to_square)
                    random_feedback = f"❌ <strong>Not quite!</strong> While this move might be legal, it ignores a threat! The opponent can respond with {op_san}, winning your {piece_lost}! Can you find the safest choice?"
                else:
                    random_refutation_from = ""
                    random_refutation_to = ""
                    random_feedback = "❌ <strong>Not quite!</strong> While this move doesn't lose material immediately, there's an even stronger option that protects your pieces or develops your position better."
                
                sq_name = chess.square_name(blunder_move.to_square)
                is_moved_into_danger = board_before.piece_at(blunder_move.from_square) is not None and not board_before.is_capture(blunder_move)
                
                if is_moved_into_danger:
                    description = "In this position, you made a move that unfortunately lost material. Can you find the safest alternative?"
                else:
                    description = "In this position, you made a capture that allowed a quick counter-attack and lost material. Look for a safer developing move instead!"
                
                opponent_move = moves[opponent_move_idx]
                
                blunder_details.append({
                    "game_num": g_idx,
                    "opponent": opponent,
                    "date": date,
                    "url": game_url,
                    "blunder_move": move_sans[player_move_idx],
                    "blunder_from": chess.square_name(blunder_move.from_square),
                    "blunder_to": chess.square_name(blunder_move.to_square),
                    "opponent_move": move_sans[opponent_move_idx],
                    "opponent_from": chess.square_name(opponent_move.from_square),
                    "opponent_to": chess.square_name(opponent_move.to_square),
                    "safe_move": safe_move_san if safe_move_san else "None",
                    "safe_from": chess.square_name(safe_move_obj.from_square) if safe_move_obj else "",
                    "safe_to": chess.square_name(safe_move_obj.to_square) if safe_move_obj else "",
                    "random_move": random_move_san,
                    "random_from": chess.square_name(random_move_obj.from_square),
                    "random_to": chess.square_name(random_move_obj.to_square),
                    "random_refutation_from": random_refutation_from,
                    "random_refutation_to": random_refutation_to,
                    "random_feedback": random_feedback,
                    "description": description,
                    "fen_before": board_before.fen(),
                    "html_board": board_to_html_grid(board_before, player_color),
                    "piece_blundered": piece_name,
                    "value_lost": abs(net_change)
                })

    print(f"Analysis complete. Found {len(blunder_details)} total material challenges in these 20 games.")
    
    puzzles = [b for b in blunder_details if b["safe_move"] != "None"]
    puzzles = sorted(puzzles, key=lambda x: x["value_lost"], reverse=True)[:4]
    
    lessons_dir = os.path.join(os.path.dirname(script_dir), "lessons")
    if not os.path.exists(lessons_dir):
        os.makedirs(lessons_dir)
        
    html_file_path = os.path.join(lessons_dir, "0002-recent-games-review.html")
    
    import random
    puzzle_cards_html = []
    for idx, p in enumerate(puzzles, 1):
        options = [
            {
                "label": p['blunder_move'], 
                "type": "blunder", 
                "from": p['blunder_from'], 
                "to": p['blunder_to'],
                "refutation_from": p.get('opponent_from', ''),
                "refutation_to": p.get('opponent_to', ''),
                "feedback": f"❌ <strong>Let's think!</strong> In the game, you played this, but it allowed the opponent to play {p['opponent_move']} and win your {p['piece_blundered']}! Look for a safe defense instead."
            },
            {
                "label": p['safe_move'], 
                "type": "correct", 
                "from": p['safe_from'], 
                "to": p['safe_to'],
                "refutation_from": '',
                "refutation_to": '',
                "feedback": "🎉 <strong>Fantastic!</strong> That move is completely safe, keeps your material protected, and helps you command the board!"
            },
            {
                "label": p['random_move'], 
                "type": "blunder", 
                "from": p['random_from'], 
                "to": p['random_to'],
                "refutation_from": p.get('random_refutation_from', ''),
                "refutation_to": p.get('random_refutation_to', ''),
                "feedback": p['random_feedback']
            }
        ]
        random.shuffle(options)
        
        letters = ['A', 'B', 'C']
        quiz_options_html = ""
        for i, opt in enumerate(options):
            quiz_options_html += f"""
                        <div class="quiz-option-container" style="display: flex; gap: 8px; margin-bottom: 0.5rem;">
                            <button class="preview-btn" style="background: var(--card-bg); border: 2px solid #334155; padding: 0.75rem; border-radius: 8px; cursor: pointer; color: white;" 
                                    onmousedown="previewMove({idx}, '{opt['from']}', '{opt['to']}')" 
                                    ontouchstart="previewMove({idx}, '{opt['from']}', '{opt['to']}')"
                                    onmouseup="resetPreview({idx})"
                                    ontouchend="resetPreview({idx})"
                                    onmouseleave="resetPreview({idx})"
                                    title="Press and hold to preview">👁️</button>
                            <div class="quiz-option" id="p{idx}-o{i+1}" style="flex: 1;"
                                 data-feedback="{opt['feedback'].replace('\"', '&quot;')}"
                                 onclick="checkPuzzle({idx}, '{opt['type']}', {i+1}, '{opt['from']}', '{opt['to']}', '{opt['refutation_from']}', '{opt['refutation_to']}')">
                                {letters[i]}) {opt['label']}
                            </div>
                        </div>"""

        puzzle_cards_html.append(f"""
        <!-- Puzzle {idx} -->
        <div class="card">
            <span class="badge">Challenge {idx}: vs {p['opponent']} ({p['date']})</span>
            <h2>Saved Position from Your Match</h2>
            <p>{p['description']}</p>
            
            <div class="chess-grid-container">
                <div class="chess-board" id="board-{idx}">
                    {p['html_board']}
                </div>
                
                <div class="explanation-side">
                    <p>What is a safer, solid choice here? <strong>Press and hold 👁️</strong> to preview the move.</p>
                    
                    <div class="quiz-container">
{quiz_options_html}
                        
                        <div id="p{idx}-feedback" class="feedback-msg"></div>
                    </div>
                </div>
            </div>
        </div>
        """)
        
    rating_history_json = json.dumps(rating_history)
    current_rating = rating_history[-1] if rating_history else 300
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lesson 2: Personalized Game Review & Progress Dashboard</title>
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

        header {{
            background: linear-gradient(135deg, #1e1b4b, #1d4ed8);
            padding: 3rem 2rem;
            text-align: center;
            border-bottom: 4px solid var(--accent-primary);
            position: relative;
            overflow: hidden;
        }}

        header::after {{
            content: '';
            position: absolute;
            bottom: -50px;
            left: -50px;
            width: 200px;
            height: 200px;
            background: var(--accent-secondary);
            filter: blur(120px);
            opacity: 0.3;
            pointer-events: none;
        }}

        header::before {{
            content: '';
            position: absolute;
            top: -50px;
            right: -50px;
            width: 200px;
            height: 200px;
            background: var(--accent-primary);
            filter: blur(120px);
            opacity: 0.3;
            pointer-events: none;
        }}

        .header-tag {{
            font-family: 'Outfit', sans-serif;
            text-transform: uppercase;
            font-weight: 800;
            font-size: 0.9rem;
            letter-spacing: 0.15rem;
            color: #60a5fa;
            margin-bottom: 0.5rem;
            display: inline-block;
        }}

        h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 2.8rem;
            font-weight: 800;
            margin: 0.5rem 0;
            background: linear-gradient(to right, #60a5fa, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .subtitle {{
            font-size: 1.2rem;
            color: var(--text-muted);
            max-width: 600px;
            margin: 0.5rem auto 0 auto;
        }}

        main {{
            max-width: 900px;
            margin: 3rem auto;
            padding: 0 1.5rem;
        }}

        .card {{
            background-color: var(--card-bg);
            border-radius: 16px;
            padding: 2.5rem;
            margin-bottom: 2.5rem;
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
            font-size: 1.8rem;
            font-weight: 700;
            margin-top: 0;
            color: #e2e8f0;
            border-left: 5px solid var(--accent-primary);
            padding-left: 0.75rem;
        }}

        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }}

        .stat-card {{
            background: rgba(15, 23, 42, 0.4);
            padding: 1.25rem;
            border-radius: 12px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.03);
        }}

        .stat-val {{
            font-size: 2.2rem;
            font-weight: 800;
            font-family: 'Outfit', sans-serif;
            color: var(--accent-secondary);
            margin-bottom: 0.25rem;
        }}

        .stat-val.win-stat {{
            color: var(--success);
        }}

        .stat-label {{
            font-size: 0.8rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05rem;
        }}

        .chess-grid-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            align-items: flex-start;
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
            font-size: 2.2rem;
            font-family: 'Segoe UI Symbol', sans-serif;
            position: relative;
            aspect-ratio: 1; /* Keep perfect square aspect ratio to prevent empty rows from collapsing */
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

        .square.light {{
            background-color: var(--board-light);
        }}

        .square.dark {{
            background-color: var(--board-dark);
        }}

        .square.highlighted::after {{
            content: '';
            width: 25px;
            height: 25px;
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
            padding: 0.75rem;
            border-radius: 8px;
            margin-bottom: 0;
            cursor: pointer;
            transition: all 0.2s ease;
            font-weight: 600;
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

        /* Chart Styling */
        .chart-container {{
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 2rem 0;
            position: relative;
        }}

        .chart-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }}

        .chart-title {{
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 1.1rem;
            color: #60a5fa;
        }}

        .chart-goal {{
            font-family: 'Outfit', sans-serif;
            font-weight: 800;
            color: #eab308;
            font-size: 0.9rem;
        }}

        .chart-svg {{
            width: 100%;
            height: auto;
            overflow: visible;
        }}

        footer {{
            text-align: center;
            padding: 2rem 0;
            color: var(--text-muted);
            font-size: 0.9rem;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            margin-top: 5rem;
        }}
    </style>
</head>
<body>

    <header>
        <div class="header-tag">Progress Review</div>
        <h1>Your Personalized Chess Board Room</h1>
        <p class="subtitle">Welcome back! Let's take a look at your daily progress and practice some shield patterns.</p>
    </header>

    <main>

        <!-- Stats Overview -->
        <section class="card">
            <span class="badge">Activity & Performance Overview</span>
            <h2>Welcome Back, Champion!</h2>
            <p>
                Fantastic job playing chess daily! Let's check in on how you've been doing. Every chess player—even grandmasters—works on keeping their pieces safe. Here is a look at your recent numbers:
            </p>
            
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-val win-stat">{wins}</div>
                    <div class="stat-label">Wins</div>
                </div>
                <div class="stat-card">
                    <div class="stat-val" style="color: var(--text-main);">{losses}</div>
                    <div class="stat-label">Losses</div>
                </div>
                <div class="stat-card" style="border-color: rgba(96,165,250,0.2);">
                    <div class="stat-val" style="color: #60a5fa;">{new_matches_count}</div>
                    <div class="stat-label">New Matches</div>
                </div>
                <div class="stat-card" style="border-color: rgba(234,179,8,0.2);">
                    <div class="stat-val" style="color: #eab308;">{current_rating}</div>
                    <div class="stat-label">Current Rating</div>
                </div>
            </div>
            
            <p>
                <em>Tip: We found {new_matches_count} new games since your last session! Let's put your piece safety skills to the test with custom puzzles from your actual matches.</em>
            </p>
        </section>

        <!-- Progress Chart Card -->
        <section class="card">
            <span class="badge">Target: 1000 Rating</span>
            <h2>Your Rating Progress Climb</h2>
            <p>Here is your rating trajectory showing how close you are to reaching the 1000 milestone! Every game played is a step forward.</p>
            
            <div class="chart-container">
                <div class="chart-header">
                    <span class="chart-title">Rating Trajectory</span>
                    <span class="chart-goal">Goal: 1000 🏆</span>
                </div>
                <svg viewBox="0 0 800 250" class="chart-svg" id="rating-chart"></svg>
            </div>
        </section>

        <!-- Dynamic Puzzle Cards -->
        {"".join(puzzle_cards_html)}

        <!-- General Training Card -->
        <section class="card">
            <span class="badge">Pro Chess Habits</span>
            <h2>Keeping Your Army Defended</h2>
            <p>
                As you keep playing, build this quick habit before every move:
            </p>
            <ol>
                <li><strong>Look at the board:</strong> Did your opponent's last move make a new threat?</li>
                <li><strong>Do a landing scan:</strong> Is the square you are moving to safe and protected?</li>
            </ol>
            <p>
                Use the **Chess.com Game Review** feature to review your games. Check out where the coach points out key defense patterns!
            </p>
        </section>

    </main>

    <footer>
        <p>Chess Mastery Journey for {player_name} • Made with 💙</p>
    </footer>

    <script>
        // Rating history data injected from python
        const ratingHistory = {rating_history_json};
        
        function drawChart() {{
            const svg = document.getElementById('rating-chart');
            if (ratingHistory.length === 0) return;
            
            const width = 800;
            const height = 220;
            const padding = 40;
            
            // Map values
            let minRating = Math.min(...ratingHistory) - 10;
            let maxRating = Math.max(...ratingHistory) + 10;
            if (maxRating - minRating < 20) {{
                maxRating = minRating + 20;
            }}
            
            const pointsCount = ratingHistory.length;
            const stepX = (width - padding * 2) / Math.max(1, pointsCount - 1);
            
            function getY(rating) {{
                const ratio = (rating - minRating) / (maxRating - minRating);
                return height - padding - ratio * (height - padding * 2);
            }}
            
            // Generate path
            let d = "";
            let dotsHTML = "";
            
            for (let i = 0; i < pointsCount; i++) {{
                const x = padding + i * stepX;
                const y = getY(ratingHistory[i]);
                
                if (i === 0) {{
                    d += `M ${{x}} ${{y}}`;
                }} else {{
                    d += ` L ${{x}} ${{y}}`;
                }}
                
                // Add glowing circles on dots
                dotsHTML += `<circle cx="${{x}}" cy="${{y}}" r="5" fill="#a78bfa" stroke="#fff" stroke-width="2">
                    <title>Game: ${{ratingHistory[i]}}</title>
                </circle>`;
            }}
            
            svg.innerHTML = `
                <!-- Gradient definition -->
                <defs>
                    <linearGradient id="line-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stop-color="#3b82f6" />
                        <stop offset="100%" stop-color="#10b981" />
                    </linearGradient>
                    <linearGradient id="area-grad" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.3" />
                        <stop offset="100%" stop-color="#10b981" stop-opacity="0.0" />
                    </linearGradient>
                </defs>
                
                <!-- Floor baseline rating grid -->
                <line x1="${{padding}}" y1="${{height - padding}}" x2="${{width - padding}}" y2="${{height - padding}}" 
                      stroke="rgba(255,255,255,0.1)" stroke-width="1" />
                <text x="${{padding - 30}}" y="${{height - padding + 4}}" fill="#94a3b8" font-size="12" font-family="Outfit">${{minRating}}</text>
                
                <!-- Current rating grid -->
                <line x1="${{padding}}" y1="${{getY(ratingHistory[pointsCount - 1])}}" x2="${{width - padding}}" y2="${{getY(ratingHistory[pointsCount - 1])}}" 
                      stroke="rgba(167, 139, 250, 0.4)" stroke-dasharray="4" stroke-width="1" />
                <text x="${{padding - 38}}" y="${{getY(ratingHistory[pointsCount - 1]) + 4}}" fill="#a78bfa" font-weight="700" font-size="12" font-family="Outfit">${{ratingHistory[pointsCount - 1]}}</text>
                
                <!-- Area fill -->
                <path d="${{d}} L ${{padding + (pointsCount-1)*stepX}} ${{height - padding}} L ${{padding}} ${{height - padding}} Z" 
                      fill="url(#area-grad)" />
                      
                <!-- Glowing rating line -->
                <path d="${{d}}" fill="none" stroke="url(#line-grad)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
                
                <!-- Dots -->
                ${{dotsHTML}}
            `;
        }}
        
        // Draw the chart on load
        window.addEventListener('load', drawChart);

        const baseBoardStates = {{}};
        const activeMoves = {{}};
        
        // Save base board states for ALL boards
        window.addEventListener('load', () => {{
            const boards = document.querySelectorAll('.chess-board');
            boards.forEach(board => {{
                // Save the base state of the board for previews
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

        function previewMove(puzzleId, fromSq, toSq) {{
            const board = document.getElementById('board-' + puzzleId);
            if (!board) return;
            
            // Revert to base state first
            board.innerHTML = baseBoardStates[board.id];
            
            // Apply the hover preview
            applyMoveToBoard(board, fromSq, toSq);
        }}
        
        function resetPreview(puzzleId) {{
            const board = document.getElementById('board-' + puzzleId);
            if (!board) return;
            
            // Revert to base state
            board.innerHTML = baseBoardStates[board.id];
            
            // Clear threat highlights
            board.querySelectorAll('.square').forEach(sq => {{
                sq.classList.remove('threat-source', 'threat-target');
            }});
            
            // If there's an active submitted move, re-apply it
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
        }}

        function checkPuzzle(puzzleId, type, optionIdx, fromSq, toSq, refutationFrom, refutationTo) {{
            // Save as active submitted move
            activeMoves[puzzleId] = {{ fromSq, toSq, refutationFrom, refutationTo, type }};
            
            const board = document.getElementById('board-' + puzzleId);
            if (!board) return;
            
            // Revert to base state
            board.innerHTML = baseBoardStates[board.id];
            
            // Clear threat highlights
            board.querySelectorAll('.square').forEach(sq => {{
                sq.classList.remove('threat-source', 'threat-target');
            }});
            
            // Visually execute the player's move
            applyMoveToBoard(board, fromSq, toSq);
            
            const feedback = document.getElementById('p' + puzzleId + '-feedback');
            feedback.style.display = 'block';
            
            // Reset styles
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
                
                // Highlight the threat attacker and target squares
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

    with open(html_file_path, "w", encoding="utf-8") as f_out:
        f_out.write(html_content)
        
    print(f"\nSuccessfully generated personalized lesson: {html_file_path}")

if __name__ == "__main__":
    main()
