import os
import platform
import chess.engine

if platform.system() == 'Windows':
    stockfish_path = './stockfish.exe'  # Local Windows path
else:
    stockfish_path = '/opt/stockfish/stockfish'  # Submission path for automarker

engine = chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True)


# Read FEN input
fen = input().strip()

# Load board from FEN
board = chess.Board(fen)

# Check if opponent's king is present
enemy_king_square = board.king(not board.turn)
movetoplay = None

# Trying to capture opponent's king directly (RBC-specific)
if enemy_king_square:
    attackers = board.attackers(board.turn, enemy_king_square)
    if attackers:
        from_square = attackers.pop()
        movetoplay = chess.Move(from_square, enemy_king_square)

# If we can't take the king, use Stockfish
if movetoplay is None:
    board.clear_stack()  # making sure Stockfish sees a clean board state
    result = engine.play(board, chess.engine.Limit(time=0.5))
    movetoplay = result.move

# Print the move in the required format
print(movetoplay.uci())


engine.quit()
