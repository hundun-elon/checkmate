import chess

fen = input() # Get current board state in FEN

board = chess.Board(fen=fen) # Create a chess board object using the FEN string

print(board) # Print visualisation of board