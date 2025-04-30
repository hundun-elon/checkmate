import chess
import reconchess

fen = input()  # Get current board state in FEN

board = chess.Board(fen=fen) # Create a chess board object using the FEN string

# Create a list to store RBC-compatible legal moves
rbc_moves = []

# Add all pseudo-legal chess moves
rbc_moves.extend(str(move) for move in board.pseudo_legal_moves)

# In RBC, '0000' represents a null move, which is legal
rbc_moves.append('0000')

# Add all legal castling moves specific to RBC
for move in reconchess.utilities.without_opponent_pieces(board).generate_castling_moves():
    if not reconchess.utilities.is_illegal_castle(board, move):
        rbc_moves.append(str(move))

# Sort the move list alphabetically
rbc_moves = sorted(rbc_moves)

# Print
for move in rbc_moves:
    print(move)