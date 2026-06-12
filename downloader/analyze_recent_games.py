import chess
import chess.pgn
import os
import sys
import json

def get_material(board, color):
    values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
    return sum(values.get(p.piece_type, 0) for p in board.piece_map().values() if p.color == color)

def quiescence(board, alpha, beta, player_color):
    stand_pat = get_material(board, player_color) - get_material(board, not player_color)
    is_player_turn = (board.turn == player_color)
    if is_player_turn:
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat
        for move in board.legal_moves:
            if board.is_capture(move):
                board.push(move)
                score = quiescence(board, alpha, beta, player_color)
                board.pop()
                if score >= beta:
                    return beta
                if score > alpha:
                    alpha = score
        return alpha
    else:
        if stand_pat <= alpha:
            return alpha
        if stand_pat < beta:
            beta = stand_pat
        for move in board.legal_moves:
            if board.is_capture(move):
                board.push(move)
                score = quiescence(board, alpha, beta, player_color)
                board.pop()
                if score <= alpha:
                    return alpha
                if score < beta:
                    beta = score
        return beta

def minimax(board, depth, alpha, beta, maximizing_player, player_color):
    if board.is_checkmate():
        return 1000 - depth if maximizing_player else -1000 + depth
    if board.is_game_over():
        return 0
    if depth == 0:
        return quiescence(board, alpha, beta, player_color)
    if maximizing_player:
        max_eval = -10000
        for move in board.legal_moves:
            board.push(move)
            evaluation = minimax(board, depth - 1, alpha, beta, False, player_color)
            board.pop()
            max_eval = max(max_eval, evaluation)
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = 10000
        for move in board.legal_moves:
            board.push(move)
            evaluation = minimax(board, depth - 1, alpha, beta, True, player_color)
            board.pop()
            min_eval = min(min_eval, evaluation)
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        return min_eval

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
            
            # Board coordinates (tiny letters/numbers like chess.com)
            show_rank = (col == 0) if is_white else (col == 7)
            show_file = (row == 0) if is_white else (row == 7)
            coord_html = ""
            if show_rank:
                coord_html += f'<span class="coord coord-rank">{row + 1}</span>'
            if show_file:
                coord_html += f'<span class="coord coord-file">{chr(ord("a") + col)}</span>'
                
            html.append(f'<div class="square {square_class}" data-square="{square_name}">{coord_html}{symbol_html}</div>')
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
    
    force_regenerate = "--force" in sys.argv or "force" in sys.argv
    if new_matches_count == 0 and not force_regenerate:
        print("No new games found since last analysis. Skipping lesson generation. (Use --force to force regeneration)")
        sys.exit(0)
    
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
            
            is_blunder = False
            if net_change <= -2:
                # Check for sacrifices/trades: look one ply ahead at the player's recapture
                if opponent_move_idx + 1 < len(moves):
                    board_after_recapture = boards[opponent_move_idx + 2]
                    mat_after_recapture = get_material(board_after_recapture, player_color) - get_material(board_after_recapture, opponent_color)
                    resolved_net_change = mat_after_recapture - mat_before
                    if resolved_net_change > -2:
                        pass # It was a planned sacrifice or trade! Not a blunder.
                    else:
                        is_blunder = True
                else:
                    is_blunder = True
            
            if is_blunder:
                blunder_move = moves[player_move_idx]
                opponent_move = moves[opponent_move_idx]
                
                board_after_blunder = board_before.copy()
                board_after_blunder.push(blunder_move)
                captured_piece = board_after_blunder.piece_at(opponent_move.to_square)
                if captured_piece:
                    piece_lost_type = captured_piece.piece_type
                else:
                    piece_lost_type = board_before.piece_at(blunder_move.from_square).piece_type if board_before.piece_at(blunder_move.from_square) else chess.PAWN
                piece_name = chess.piece_name(piece_lost_type).capitalize()
                
                if net_change <= -7: queen_blunders += 1
                elif net_change <= -4: rook_blunders += 1
                else: minor_blunders += 1
                
                safe_move_obj, safe_move_san = find_safe_move(board_before, player_color)
                if not safe_move_obj:
                    continue
                
                import random
                # Find an alternative plausible move
                legal_moves = list(board_before.legal_moves)
                alt_move_objs = [m for m in legal_moves if m != blunder_move and m != safe_move_obj]
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
                    description = "Find a safer alternative to keep your material."
                else:
                    description = "Find a safer developing move instead of this capture."
                
                opponent_move = moves[opponent_move_idx]
                is_promo = opponent_move.promotion is not None
                if is_promo:
                    promo_piece = chess.piece_name(opponent_move.promotion).capitalize()
                    blunder_feedback = f"❌ <strong>Let's think!</strong> In the game, you played this, but it allowed the opponent to play {move_sans[opponent_move_idx]} and promote to a {promo_piece}! Look for a safe defense instead."
                else:
                    blunder_feedback = f"❌ <strong>Let's think!</strong> In the game, you played this, but it allowed the opponent to play {move_sans[opponent_move_idx]} and win your {piece_name}! Look for a safe defense instead."
                
                blunder_details.append({
                    "puzzle_type": "blunder",
                    "game_num": g_idx,
                    "opponent": opponent,
                    "date": date,
                    "url": game_url,
                    "played_move": move_sans[player_move_idx],
                    "played_from": chess.square_name(blunder_move.from_square),
                    "played_to": chess.square_name(blunder_move.to_square),
                    "opponent_move": move_sans[opponent_move_idx],
                    "opponent_from": chess.square_name(opponent_move.from_square),
                    "opponent_to": chess.square_name(opponent_move.to_square),
                    "correct_move": safe_move_san,
                    "correct_from": chess.square_name(safe_move_obj.from_square),
                    "correct_to": chess.square_name(safe_move_obj.to_square),
                    "incorrect_move": random_move_san,
                    "incorrect_from": chess.square_name(random_move_obj.from_square),
                    "incorrect_to": chess.square_name(random_move_obj.to_square),
                    "incorrect_refutation_from": random_refutation_from,
                    "incorrect_refutation_to": random_refutation_to,
                    "incorrect_feedback": random_feedback,
                    "played_feedback": blunder_feedback,
                    "correct_feedback": "🎉 <strong>Fantastic!</strong> That move is completely safe, keeps your material protected, and helps you command the board!",
                    "description": description,
                    "fen_before": board_before.fen(),
                    "html_board": board_to_html_grid(board_before, player_color),
                    "value_lost": abs(net_change)
                })
            else:
                actual_move = moves[player_move_idx]
                candidates = []
                for opt_move in board_before.legal_moves:
                    if opt_move == actual_move:
                        continue
                    if board_before.is_capture(opt_move) or board_before.gives_check(opt_move) or opt_move.promotion:
                        candidates.append(opt_move)
                
                if candidates:
                    board_before.push(actual_move)
                    actual_eval = minimax(board_before, depth=1, alpha=-10000, beta=10000, maximizing_player=False, player_color=player_color)
                    board_before.pop()
                    
                    best_opt_move = None
                    best_opt_eval = -10000
                    
                    for opt_move in candidates:
                        board_before.push(opt_move)
                        opt_eval = minimax(board_before, depth=1, alpha=-10000, beta=10000, maximizing_player=False, player_color=player_color)
                        board_before.pop()
                        if opt_eval > best_opt_eval:
                            best_opt_eval = opt_eval
                            best_opt_move = opt_move
                            
                    if best_opt_move and (best_opt_eval - actual_eval) >= 1.5 and best_opt_eval >= 0:
                        opt_move_san = board_before.san(best_opt_move)
                        
                        import random
                        legal_moves = list(board_before.legal_moves)
                        alt_move_objs = [m for m in legal_moves if m != actual_move and m != best_opt_move]
                        random_move_obj = random.choice(alt_move_objs) if alt_move_objs else actual_move
                        random_move_san = board_before.san(random_move_obj)
                        
                        blunder_details.append({
                            "puzzle_type": "missed_opportunity",
                            "game_num": g_idx,
                            "opponent": opponent,
                            "date": date,
                            "url": game_url,
                            "played_move": move_sans[player_move_idx],
                            "played_from": chess.square_name(actual_move.from_square),
                            "played_to": chess.square_name(actual_move.to_square),
                            "opponent_move": "",
                            "opponent_from": "",
                            "opponent_to": "",
                            "correct_move": opt_move_san,
                            "correct_from": chess.square_name(best_opt_move.from_square),
                            "correct_to": chess.square_name(best_opt_move.to_square),
                            "incorrect_move": random_move_san,
                            "incorrect_from": chess.square_name(random_move_obj.from_square),
                            "incorrect_to": chess.square_name(random_move_obj.to_square),
                            "incorrect_refutation_from": "",
                            "incorrect_refutation_to": "",
                            "incorrect_feedback": "❌ <strong>Not quite!</strong> There is a much stronger tactical option available here that wins material.",
                            "played_feedback": f"❌ <strong>Not quite!</strong> In the game, you played {move_sans[player_move_idx]}. It was safe, but you missed a strong tactical opportunity to play {opt_move_san} which wins material!",
                            "correct_feedback": f"🎉 <strong>Fantastic!</strong> That is the strong tactical opportunity! This move wins material and gains a medium-term advantage.",
                            "description": "Find the tactical shot that wins material or gains a major advantage.",
                            "fen_before": board_before.fen(),
                            "html_board": board_to_html_grid(board_before, player_color),
                            "value_lost": best_opt_eval - actual_eval
                        })

    print(f"Analysis complete. Found {len(blunder_details)} total material challenges in these 20 games.")
    
    # We will define puzzles dynamically after determining the lesson number below
    
    lessons_dir = os.path.join(os.path.dirname(script_dir), "lessons")
    if not os.path.exists(lessons_dir):
        os.makedirs(lessons_dir)
        
    # Dynamically find the highest numbered lesson in the lessons directory
    import glob
    import re
    files = glob.glob(os.path.join(lessons_dir, "*.html"))
    max_num = 1  # Preserve Lesson 1 as static
    for f in files:
        basename = os.path.basename(f)
        match = re.match(r"^(\d+)", basename)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
                
    if new_matches_count > 0:
        # Create a new lesson file
        lesson_num = max_num + 1
    else:
        # Overwrite the latest lesson (or create Lesson 2 if only Lesson 1 exists)
        lesson_num = max(2, max_num)
        
    filename = f"{lesson_num:04d}-recent-games-review.html"
    html_file_path = os.path.join(lessons_dir, filename)
    
    used_puzzles_path = os.path.join(script_dir, "used_puzzles.txt")
    used_puzzles = {} # map of identifier -> lesson_num
    if os.path.exists(used_puzzles_path):
        try:
            with open(used_puzzles_path, "r", encoding="utf-8") as uf:
                for line in uf:
                    line_str = line.strip()
                    if line_str and "_" in line_str:
                        parts = line_str.split("_", 1)
                        if len(parts) == 2:
                            l_num = int(parts[0])
                            p_id = parts[1]
                            used_puzzles[p_id] = l_num
        except Exception as e:
            print(f"Warning: could not read used_puzzles.txt: {e}")

    puzzles = []
    for b in blunder_details:
        if b.get("correct_move") == "None" or b.get("correct_move") == "":
            continue
        p_id = f"{b['url']}_{b['played_move']}"
        # Filter out if already used in a previous lesson
        if p_id in used_puzzles:
            # If we are overwriting the latest lesson, allow reusing puzzles from that same lesson
            if new_matches_count > 0 or used_puzzles[p_id] < lesson_num:
                continue
        puzzles.append(b)

    puzzles = sorted(puzzles, key=lambda x: x["value_lost"], reverse=True)[:10]
    
    import random
    puzzle_cards_html = []
    for idx, p in enumerate(puzzles, 1):
        options = [
            {
                "label": p['played_move'], 
                "type": "blunder", 
                "from": p['played_from'], 
                "to": p['played_to'],
                "refutation_from": p.get('opponent_from', ''),
                "refutation_to": p.get('opponent_to', ''),
                "feedback": p['played_feedback']
            },
            {
                "label": p['correct_move'], 
                "type": "correct", 
                "from": p['correct_from'], 
                "to": p['correct_to'],
                "refutation_from": '',
                "refutation_to": '',
                "feedback": p['correct_feedback']
            },
            {
                "label": p['incorrect_move'], 
                "type": "blunder", 
                "from": p['incorrect_from'], 
                "to": p['incorrect_to'],
                "refutation_from": p.get('incorrect_refutation_from', ''),
                "refutation_to": p.get('incorrect_refutation_to', ''),
                "feedback": p['incorrect_feedback']
            }
        ]
        random.shuffle(options)
        
        letters = ['A', 'B', 'C']
        quiz_options_html = ""
        for i, opt in enumerate(options):
            quiz_options_html += f"""
                        <div class="quiz-option-container" style="display: flex; gap: 8px; margin-bottom: 0.5rem;">
                            <button class="preview-btn" onclick="togglePreview(this, {idx}, '{opt['from']}', '{opt['to']}', {i+1})" title="Tap to toggle move preview">👁️</button>
                            <div class="quiz-option" id="p{idx}-o{i+1}" style="flex: 1;"
                                 data-feedback="{opt['feedback'].replace('\"', '&quot;')}"
                                  onclick="checkPuzzle({idx}, '{opt['type']}', {i+1}, '{opt['from']}', '{opt['to']}', '{opt['refutation_from']}', '{opt['refutation_to']}')">
                                {letters[i]}) {opt['label']}
                            </div>
                        </div>"""

        if p.get("puzzle_type") == "missed_opportunity":
            badge_text = f"Opp {idx} vs {p['opponent']}"
            title_text = "Tactical Opportunity"
        else:
            badge_text = f"Safety {idx} vs {p['opponent']}"
            title_text = "Hanging Piece"

        puzzle_cards_html.append(f"""
        <!-- Puzzle {idx} -->
        <div class="card">
            <span class="badge">{badge_text}</span>
            <h2>{title_text}</h2>
            <p>{p['description']}</p>
            
            <div class="chess-grid-container">
                <div class="chess-board" id="board-{idx}">
                    {p['html_board']}
                </div>
                
                <div class="explanation-side">
                    <div class="quiz-container">
{quiz_options_html}
                        
                        <div id="p{idx}-feedback" class="feedback-msg"></div>
                    </div>
                </div>
            </div>
        </div>
        """)
        
    current_rating = rating_history[-1] if rating_history else 300
    html_content = f"""<!-- LESSON_METADATA: {{"num": {lesson_num}, "wins": {wins}, "losses": {losses}, "rating": {current_rating}, "challenges": {len(puzzles)}}} -->
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
        {"".join(puzzle_cards_html)}
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

    with open(html_file_path, "w", encoding="utf-8") as f_out:
        f_out.write(html_content)

    # Save user_stats.json
    stats_data = {
        "username": player_name,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "new_matches_count": new_matches_count,
        "current_rating": current_rating,
        "rating_history": rating_history,
        "queen_blunders": queen_blunders,
        "rook_blunders": rook_blunders,
        "minor_blunders": minor_blunders
    }
    stats_path = os.path.join(script_dir, "user_stats.json")
    try:
        with open(stats_path, "w", encoding="utf-8") as sf:
            json.dump(stats_data, sf, indent=4)
        print(f"Successfully saved user stats to {stats_path}")
    except Exception as e:
        print(f"Warning: could not write to user_stats.json: {e}")
        
    # Clean up entries for current lesson or greater to avoid duplicates, then write new used puzzles
    lines_to_keep = []
    if os.path.exists(used_puzzles_path):
        try:
            with open(used_puzzles_path, "r", encoding="utf-8") as uf:
                for line in uf:
                    line_str = line.strip()
                    if line_str and "_" in line_str:
                        parts = line_str.split("_", 1)
                        if len(parts) == 2:
                            try:
                                l_num = int(parts[0])
                                if l_num < lesson_num:
                                    lines_to_keep.append(line_str)
                            except:
                                pass
        except:
            pass
            
    try:
        with open(used_puzzles_path, "w", encoding="utf-8") as uf:
            for line_str in lines_to_keep:
                uf.write(line_str + "\n")
            for p in puzzles:
                p_id = f"{p['url']}_{p['played_move']}"
                uf.write(f"{lesson_num:04d}_{p_id}\n")
    except Exception as e:
        print(f"Warning: could not write to used_puzzles.txt: {e}")
        
    print(f"\nSuccessfully generated personalized lesson: {html_file_path}")

if __name__ == "__main__":
    main()
