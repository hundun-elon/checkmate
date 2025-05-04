import chess
import reconchess

# Read the input FEN string and remove any extra spaces
fen = input().strip()

 #chess thing expects a single "-" instead.incase input have --
parts = fen.split()
if parts[2] == "--":
    parts[2] = "-"
fen = " ".join(parts)

# Creating a chess board from the cleaned-up FEN string
board = chess.Board(fen)

# We'll store all resulting board states (as FEN strings) in a set to avoid duplicates
fen_set = set()

#  "null move" ( skip their turn)
# the null move is not allowed if the player is currently in check.
#  only adding it if the king is safe.
if not board.is_check():
    null_board = board.copy()
    null_board.push(chess.Move.null())  # Apply the null move
    fen_set.add(null_board.fen())       # Save the resulting board state

# Add all  legal moves. These include most normal chess moves,

for move in board.pseudo_legal_moves:
    new_board = board.copy()
    new_board.push(move)                # Apply the move
    fen_set.add(new_board.fen())        # Save the resulting board state


# We use helper functions from the reconchess package to generate RBC special castling rules.
for move in reconchess.utilities.without_opponent_pieces(board).generate_castling_moves():
    if not reconchess.utilities.is_illegal_castle(board, move):
        new_board = board.copy()
        new_board.push(move)            # Apply the legal RBC-style castling move
        fen_set.add(new_board.fen())    # Save the resulting board state

# sort all resulting FEN strings alphabetically and print them one per line
for f in sorted(fen_set):
    print(f)
