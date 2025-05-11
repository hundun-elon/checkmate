# import os
# import platform
# import chess.engine

# if platform.system() == 'Windows':
#     stockfish_path = './stockfish.exe'  # Local Windows path
# else:
#     stockfish_path = '/opt/stockfish/stockfish'  # Submission path for automarker

# engine = chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True)


# # Read FEN input
# fen = input().strip()

# # Load board from FEN
# board = chess.Board(fen)

# # Check if opponent's king is present
# enemy_king_square = board.king(not board.turn)
# movetoplay = None

# # Trying to capture opponent's king directly (RBC-specific)
# if enemy_king_square:
#     attackers = board.attackers(board.turn, enemy_king_square)
#     if attackers:
#         from_square = attackers.pop()
#         movetoplay = chess.Move(from_square, enemy_king_square)

# # If we can't take the king, use Stockfish
# if movetoplay is None:
#     board.clear_stack()  # making sure Stockfish sees a clean board state
#     result = engine.play(board, chess.engine.Limit(time=0.5))
#     movetoplay = result.move

# # Print the move in the required format
# print(movetoplay.uci())


# engine.quit()


import os
import platform
import chess.engine

# Find the stockfish executable in the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
stockfish_path = os.path.join(current_dir, 'stockfish.exe')

# Make sure the file exists
if not os.path.exists(stockfish_path):
#     print(f"Error: Stockfish executable not found at {stockfish_path}")
    # Try alternative paths
    if platform.system() == 'Windows':
        stockfish_path = './stockfish.exe'  # Local Windows path
    else:
        # Try the current directory without path manipulation
        stockfish_path = './stockfish.exe'
        if not os.path.exists(stockfish_path):
            # print(f"Error: Stockfish not found at {stockfish_path} either")
            # print("Please ensure stockfish is in the current directory")
            exit(1)

# print(f"Using Stockfish at: {stockfish_path}")

try:
    # Open the engine
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
    
    # Clean up
    engine.quit()
except Exception as e:
    print(f"An error occurred: {e}")