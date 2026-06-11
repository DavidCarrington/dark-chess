import chess
import chess.pgn
import os
import sys

def get_material_value(board):
    # Standard chess piece values
    values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0
    }
    white_val = 0
    black_val = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            val = values.get(piece.piece_type, 0)
            if piece.color == chess.WHITE:
                white_val += val
            else:
                black_val += val
    return white_val, black_val

def analyze_pgn(pgn_filename, target_player):
    if not os.path.exists(pgn_filename):
        print(f"Error: {pgn_filename} not found.")
        sys.exit(1)

    target_player_lower = target_player.lower()
    
    total_games = 0
    wins = 0
    losses = 0
    draws = 0
    
    white_games = 0
    white_wins = 0
    white_losses = 0
    white_draws = 0
    
    black_games = 0
    black_wins = 0
    black_losses = 0
    black_draws = 0

    # Loss types
    loss_by_checkmate = 0
    loss_by_resignation = 0
    loss_by_timeout = 0
    loss_by_abandonment = 0
    loss_other = 0

    # Win types
    win_by_checkmate = 0
    win_by_resignation = 0
    win_by_timeout = 0
    win_other = 0

    # Openings as White (Move 1)
    white_openings = {}
    # Openings as Black (Opponent Move 1 -> Black response)
    black_responses = {}

    # Short games (lost in <= 12 moves)
    miniature_losses = []
    
    # Blunder statistics (material drops)
    queen_blunders = 0
    rook_blunders = 0
    minor_blunders = 0 # Knight/Bishop
    
    print("Reading and analyzing games... (this may take a few seconds)")

    with open(pgn_filename, "r", encoding="utf-8") as pgn_file:
        while True:
            game = chess.pgn.read_game(pgn_file)
            if game is None:
                break
                
            headers = game.headers
            white = headers.get("White", "")
            black = headers.get("Black", "")
            result = headers.get("Result", "")
            game_url = headers.get("Link", headers.get("url", ""))
            
            is_white = white.lower() == target_player_lower
            is_black = black.lower() == target_player_lower
            
            if not (is_white or is_black):
                continue
                
            total_games += 1
            
            # Determine game outcome for target player
            player_won = False
            player_lost = False
            player_drew = False
            
            if result == "1-0":
                if is_white:
                    player_won = True
                else:
                    player_lost = True
            elif result == "0-1":
                if is_black:
                    player_won = True
                else:
                    player_lost = True
            elif result in ["1/2-1/2", "1/2"]:
                player_drew = True
            else:
                # Unfinished or unknown
                continue
                
            # Track color stats
            if is_white:
                white_games += 1
                if player_won:
                    white_wins += 1
                elif player_lost:
                    white_losses += 1
                else:
                    white_draws += 1
            elif is_black:
                black_games += 1
                if player_won:
                    black_wins += 1
                elif player_lost:
                    black_losses += 1
                else:
                    black_draws += 1

            if player_won:
                wins += 1
            elif player_lost:
                losses += 1
            else:
                draws += 1

            # Analyze termination/termination text
            # Chess.com PGN termination is typically in the "Termination" header
            termination = headers.get("Termination", "").lower()
            if player_lost:
                if "checkmate" in termination:
                    loss_by_checkmate += 1
                elif "resigned" in termination or "resignation" in termination:
                    loss_by_resignation += 1
                elif "time" in termination or "timeout" in termination:
                    loss_by_timeout += 1
                elif "abandoned" in termination:
                    loss_by_abandonment += 1
                else:
                    loss_other += 1
            elif player_won:
                if "checkmate" in termination:
                    win_by_checkmate += 1
                elif "resigned" in termination or "resignation" in termination:
                    win_by_resignation += 1
                elif "time" in termination or "timeout" in termination:
                    win_by_timeout += 1
                else:
                    win_other += 1

            # Play through the game to get move count and track material
            board = game.board()
            moves = list(game.mainline_moves())
            move_count = (len(moves) + 1) // 2
            
            # Store short losses
            if player_lost and move_count <= 12:
                game_date = headers.get("Date", "Unknown Date")
                miniature_losses.append({
                    "opponent": black if is_white else white,
                    "moves": move_count,
                    "url": game_url,
                    "result": "Checkmate" if "checkmate" in termination else "Other",
                    "date": game_date
                })

            # Check opening moves
            if len(moves) >= 1:
                first_move_white = board.san(moves[0])
                if is_white:
                    # White opening distribution
                    white_openings[first_move_white] = white_openings.get(first_move_white, {"games": 0, "wins": 0})
                    white_openings[first_move_white]["games"] += 1
                    if player_won:
                        white_openings[first_move_white]["wins"] += 1
                elif is_black and len(moves) >= 2:
                    board.push(moves[0])
                    first_move_black = board.san(moves[1])
                    key = f"{first_move_white} -> {first_move_black}"
                    black_responses[key] = black_responses.get(key, {"games": 0, "wins": 0})
                    black_responses[key]["games"] += 1
                    if player_won:
                        black_responses[key]["wins"] += 1

            # Reset board for material tracking
            board = game.board()
            prev_white_val, prev_black_val = get_material_value(board)
            
            # We look for moves where the player's material dropped significantly
            # and they didn't recapture on the very next move.
            for index, move in enumerate(moves):
                current_player_color = board.turn
                board.push(move)
                
                new_white_val, new_black_val = get_material_value(board)
                
                # Check if it was the target player's turn that just moved
                was_target_player_turn = (current_player_color == chess.WHITE and is_white) or \
                                         (current_player_color == chess.BLACK and is_black)
                
                # We want to identify when the target player loses material.
                # Usually, a material loss happens on the *opponent's* turn (the opponent captures a piece).
                # If the target player doesn't recapture on their next turn, it's a net material loss.
                # Let's track the net change for target player after their response.
                if not was_target_player_turn:
                    # Opponent just made a move (captured something or attacked).
                    # Let's see if the target player's material went down.
                    target_lost_val = 0
                    if is_white:
                        target_lost_val = prev_white_val - new_white_val
                    else:
                        target_lost_val = prev_black_val - new_black_val
                        
                    if target_lost_val > 0:
                        # Opponent captured a piece! Let's check the target player's response (recapture).
                        next_index = index + 1
                        recaptured_val = 0
                        if next_index < len(moves):
                            # Play the target player's move
                            board.push(moves[next_index])
                            temp_white_val, temp_black_val = get_material_value(board)
                            
                            # See what target player captured
                            if is_white:
                                recaptured_val = prev_black_val - temp_black_val
                            else:
                                recaptured_val = prev_white_val - temp_white_val
                            
                            # pop the move we temporarily pushed
                            board.pop()
                            
                        net_loss = target_lost_val - recaptured_val
                        if net_loss >= 2:
                            # Blunder!
                            if net_loss >= 7:
                                queen_blunders += 1
                            elif net_loss >= 4:
                                rook_blunders += 1
                            else:
                                minor_blunders += 1
                                
                prev_white_val, prev_black_val = new_white_val, new_black_val

    # Print Report
    print("\n" + "=" * 50)
    print(f"CHESS.COM GAME ANALYSIS REPORT FOR {target_player}")
    print("=" * 50)
    print(f"Total Games Scanned: {total_games}")
    print(f"Overall Record: {wins} Wins / {losses} Losses / {draws} Draws (Win Rate: {wins/total_games*100:.1f}%)")
    
    print("\n--- RESULTS BY PIECE COLOR ---")
    if white_games > 0:
        print(f"As White: {white_wins}W / {white_losses}L / {white_draws}D (Win Rate: {white_wins/white_games*100:.1f}% in {white_games} games)")
    else:
        print("As White: No games played.")
    if black_games > 0:
        print(f"As Black: {black_wins}W / {black_losses}L / {black_draws}D (Win Rate: {black_wins/black_games*100:.1f}% in {black_games} games)")
    else:
        print("As Black: No games played.")

    print("\n--- HOW LOSSES OCCUR ---")
    if losses > 0:
        print(f"Checkmate:   {loss_by_checkmate} ({loss_by_checkmate/losses*100:.1f}%)")
        print(f"Resignation: {loss_by_resignation} ({loss_by_resignation/losses*100:.1f}%)")
        print(f"Timeout:     {loss_by_timeout} ({loss_by_timeout/losses*100:.1f}%)")
        print(f"Abandoned:   {loss_by_abandonment} ({loss_by_abandonment/losses*100:.1f}%)")
    else:
        print("No losses recorded.")

    print("\n--- HOW WINS OCCUR ---")
    if wins > 0:
        print(f"Checkmate:   {win_by_checkmate} ({win_by_checkmate/wins*100:.1f}%)")
        print(f"Resignation: {win_by_resignation} ({win_by_resignation/wins*100:.1f}%)")
        print(f"Timeout:     {win_by_timeout} ({win_by_timeout/wins*100:.1f}%)")
    else:
        print("No wins recorded.")

    print("\n--- PIECE BLUNDERS (Material Drops of >= 2 points) ---")
    total_blunders = queen_blunders + rook_blunders + minor_blunders
    print(f"Estimated major piece blunders: {total_blunders} times in {total_games} games")
    print(f"• Queen drops (9 pts):    {queen_blunders} times")
    print(f"• Rook drops (5 pts):     {rook_blunders} times")
    print(f"• Knight/Bishop (3 pts):  {minor_blunders} times")
    print(f"Average: {total_blunders/total_games:.2f} major blunders per game.")

    print("\n--- WHITE OPENINGS (Move 1) ---")
    sorted_white = sorted(white_openings.items(), key=lambda x: x[1]["games"], reverse=True)
    for move, stats in sorted_white[:5]:
        wr = stats["wins"] / stats["games"] * 100
        print(f"• {move}: {stats['games']} games (Win Rate: {wr:.1f}%)")

    print("\n--- BLACK RESPONSES (Opponent Move 1 -> Black Response) ---")
    sorted_black = sorted(black_responses.items(), key=lambda x: x[1]["games"], reverse=True)
    for setup, stats in sorted_black[:5]:
        wr = stats["wins"] / stats["games"] * 100
        print(f"• {setup}: {stats['games']} games (Win Rate: {wr:.1f}%)")

    print("\n--- SHORT LOSSES (<= 12 Moves) ---")
    print(f"Total early miniature losses: {len(miniature_losses)}")
    if miniature_losses:
        print("Here are the 5 most recent early losses. Use these URLs on Chess.com to do a Game Review:")
        # Show most recent first
        recent_losses = list(reversed(miniature_losses[-5:]))
        for idx, ml in enumerate(recent_losses, 1):
            print(f" {idx}. [{ml['date']}] Lost in {ml['moves']} moves vs {ml['opponent']} (Type: {ml['result']})")
            if ml["url"]:
                print(f"    Link: {ml['url']}")
    print("=" * 50)

if __name__ == "__main__":
    player = sys.argv[1] if len(sys.argv) > 1 else "darkkkkkkk0"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pgn = os.path.join(script_dir, f"{player}_games.pgn")
    analyze_pgn(pgn, player)
