import chess
from typing import List, Tuple, Optional

# Read the number of FEN states to process
num_states = int(input())

# Read and store all the input FEN strings as Board objects
potential_states: List[chess.Board] = []
for _ in range(num_states):
    fen_str = input()
    potential_states.append(chess.Board(fen=fen_str))

# Read the sensing result string
sense_input = input()

# Parse the sensing result into a list of (square : expected piece), '?' means the square is expected to be empty
sense_result: List[Tuple[int, Optional[chess.Piece]]] = []
for item in sense_input.split(";"):
    if not item:  # Skip empty strings from trailing semicolon
        continue
    square_str, piece_str = item.split(":")
    square = chess.parse_square(square_str)
    piece = None if piece_str == "?" else chess.Piece.from_symbol(piece_str)
    sense_result.append((square, piece))

# Filter out inconsistent states based on the sensing result
consistent_states: List[chess.Board] = []
for state in potential_states:
    match = True
    for square, expected_piece in sense_result:
        actual_piece = state.piece_at(square)
        if actual_piece != expected_piece:
            match = False
            break
    if match:
        consistent_states.append(state)

# Output the FENs of consistent states, sorted alphabetically
for board in sorted(consistent_states, key=lambda b: b.fen()):
    print(board.fen())
