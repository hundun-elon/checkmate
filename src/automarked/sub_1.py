import chess

fen = input()

board = chess.Board(fen=fen)

print(board)