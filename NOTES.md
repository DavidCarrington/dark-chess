# Teaching Notes

## User Preferences
- **Student Profile**: 11 years old, plays daily, chess.com username `darkkkkkkk0` (Rapid rating: 347).
- **Resources Available**: Chess.com full-tier premium subscription (unlimited puzzles, game reviews).
- **Goal**: Reach 1000 rating.
- **Approach**: Leverage data/analysis tools to scan their PGN games to find repetitive blunder patterns, and structure lessons around those patterns. Support (not replace) Chess.com learning materials.

## Working Notes
- **Analysis Idea**: We can write a Python script using `python-chess` to process `downloader/darkkkkkkk0_games.pgn`.
- **Key Metrics to Scan**:
  - Openings played (e.g. how often they play 1.e4 vs 1.d4, and their win rates in each).
  - Game endings (checkmate, timeout, resignation, abandonment).
  - Blunder detection (moves where evaluation changes drastically, or where material is hung).
- **Personalized Analyzer & Lesson Generator**:
  - Created `downloader/analyze_recent_games.py` to scan the last 20 games and detect exact material blunders.
  - Automatically compiles a personalized interactive review page (`lessons/0002-recent-games-review.html`).

## Lesson Design Guidelines
1. **Reference UI Template:** Use `lessons/0002-recent-games-review.html` as the visual and interaction gold standard for all future interactive lessons. It incorporates critical solutions for:
   - **Responsive Board:** `max-width: 100%; aspect-ratio: 1` sizing.
   - **Vertical Condensation:** Compact padding/margins for mobile visibility.
   - **Interaction:** Tap-to-preview button, permanent piece movement on submission.
   - **Piece Rendering:** `data-square` attributes for targeting and explicit `<span class="piece white">` text-shadowing.
   - **Board Orientation:** The board must always be flipped appropriately (a8 top-left for White, h1 top-left for Black) so the user always sees the board from their own perspective.
2. **Context & Tracking:** Always include the compile date and the number of new matches found since the last session. Render a self-contained SVG rating progress chart.
3. **Puzzles:** Provide at least 3 subtle move options without hints. 
   - **No Spoilers:** The prompt/description must never state which piece was moved or where it went, as this gives away which multiple-choice option to avoid.
   - When evaluating the answer, give *specific justification* (e.g., "This allows Qxc6, winning your Knight!").
