import chess
import reconchess

# Read input FEN and capture square
fen = input().strip()
capture_square_str = input().strip()

# Normalize FEN for castling 
parts = fen.split()
if parts[2] == '--':
    parts[2] = '-'
elif parts[2].endswith('-') and parts[2] != '-':
    parts[2] = parts[2][:-1]
while len(parts) < 6:
    parts.insert(3, '-')
fen = " ".join(parts)

# Create board from cleaned FEN
board = chess.Board(fen)

# Convert square name like 'e5' into a square index
capture_square = chess.parse_square(capture_square_str)

# Store resulting FENs
fen_set = set()

# Add all pseudo-legal capturing moves to the set
for move in board.pseudo_legal_moves:
    if board.is_capture(move) and move.to_square == capture_square:
        new_board = board.copy()
        new_board.push(move)
        fen_set.add(new_board.fen())

# Include RBC-specific castling if they capture (rare, but safe to check)
for move in reconchess.utilities.without_opponent_pieces(board).generate_castling_moves():
    if not reconchess.utilities.is_illegal_castle(board, move) and move.to_square == capture_square:
        new_board = board.copy()
        new_board.push(move)
        fen_set.add(new_board.fen())

# Output sorted FENs
for f in sorted(fen_set):
    print(f)
