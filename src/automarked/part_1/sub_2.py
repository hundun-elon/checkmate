import chess

fen = input()  # Get current board state in FEN

board = chess.Board(fen=fen) # Create a chess board object using the FEN string

uci = input()  # Get move in UCI format

move = chess.Move.from_uci(uci) # Create a move object

board.push(move)  # Apply the move

print(board.fen())  # Print updated board state in FEN
