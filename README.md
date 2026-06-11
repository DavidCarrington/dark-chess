# Chess Mastery Portal 🏆

Welcome to your personalized Chess Mastery Portal! This repository downloads recent Chess.com games, analyzes them for material blunders, and automatically compiles interactive review lessons and a central dashboard.

## Features
- **Dynamic Blunder Scanner**: Scans recent matches using `python-chess` to identify material blunders.
- **Interactive Chess Review**: Web pages rendered with visual move previews and dynamic chessboards for puzzle practice.
- **Centralized Dashboard**: A portal homepage (`index.html`) that lists all generated lessons, stats, and rating progress.
- **Automated Pipeline**: Rebuilds the dashboard and new review lessons automatically with a single script execution.

## Getting Started

### Prerequisites
Make sure you have python-chess installed:
```bash
pip install python-chess
```

### Running the Update
To fetch new games from Chess.com and rebuild your lessons and dashboard index, run:
```bash
update.bat
```
or run the python script directly:
```bash
python update.py
```
This will rebuild `index.html` at the project root and output the new lessons to `/lessons/`.

---
*Created with 💙 for darkkkkkkk0's chess journey.*
