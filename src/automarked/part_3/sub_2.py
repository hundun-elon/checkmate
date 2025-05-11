import os
import sys
import platform
import chess
import chess.engine
from collections import Counter

def select_move(board, engine=None):
    """
    Given a chess board, select a move by:
    1. Capturing the opponent's king if possible
    2. Otherwise, ask Stockfish for a move using the shared engine
    """
    # Check if opponent's king is present
    enemy_king_square = board.king(not board.turn)
    
    # Try to capture enemy king (RBC rules)
    if enemy_king_square is not None:
        attackers = board.attackers(board.turn, enemy_king_square)
        if attackers:
            from_square = attackers.pop()
            return chess.Move(from_square, enemy_king_square)
    
    board.clear_stack()

    try:
        if engine is not None:
            result = engine.play(board, chess.engine.Limit(time=0.1))  # Faster lookup
            return result.move
    except Exception as e:
        print(f"Error with Stockfish: {e}", file=sys.stderr)
    
    # Fallback move
    try:
        legal_moves = list(board.legal_moves)
        return legal_moves[0] if legal_moves else chess.Move.null()
    except:
        return chess.Move.null()


def process_multiple_boards():
    """
    Read multiple FENs, find the best move per board, and return the most common one.
    """
    try:
        n = int(input().strip())
        fens = [input().strip() for _ in range(n)]
        moves = []

        # Determine correct Stockfish path
        if platform.system() == 'Windows':
            stockfish_path = './stockfish.exe'
        else:
            stockfish_path = '/opt/stockfish/stockfish'
            if not os.path.exists(stockfish_path):
                if os.path.exists('./stockfish'):
                    stockfish_path = './stockfish'
                elif os.path.exists('./stockfish.exe'):
                    stockfish_path = './stockfish.exe'

        try:
            engine = chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True)

            for fen in fens:
                board = chess.Board(fen)
                move = select_move(board, engine=engine)
                moves.append(move.uci())

            engine.quit()

        except Exception as e:
            print(f"Error with Stockfish: {e}", file=sys.stderr)
            return None

        # Analyze most common move
        move_counter = Counter(moves)
        max_count = max(move_counter.values())
        most_common_moves = [move for move, count in move_counter.items() if count == max_count]
        most_common_moves.sort()
        return most_common_moves[0]

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    recommended_move = process_multiple_boards()
    if recommended_move:
        print(recommended_move)
