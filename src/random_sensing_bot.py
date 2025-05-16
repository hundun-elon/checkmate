import chess.engine
import reconchess
from reconchess import *
import random
from typing import Optional, List, Tuple, Set
from collections import Counter

class RandomSensingBot(Player):
    def __init__(self):
        # set of possible board states
        self.boards: Set[str] = set()
        self.color = None
        self.turn_num = None
        print("[DEBUG] Bot initialised")

        self.engine = chess.engine.SimpleEngine.popen_uci('./engines/stockfish', setpgrp=True)
        print("[DEBUG] Stockfish engine started")

    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        # add initial board state to set
        self.boards = {board.fen()}
        self.color = color
        self.turn_num = 0

        color_name = "White" if color else "Black"
        print(f"[DEBUG] Game started. Color: {color_name}, Opponent: {opponent_name}")

    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square]):
        self.turn_num += 1
        print(f"[DEBUG] Opponent move result. Captured: {captured_my_piece}, Square: {capture_square}")

        # skip this function if this is the first turn and we're playing as White
        if self.turn_num == 1 and self.color == chess.WHITE:
            return

        # set to store updated board positions after simulating opponent moves
        new_boards = set()

        # case 1: piece was captured
        # find all moves that result in a capture move at the capture square - this includes rbc modified moves
        # generate new boards from those moves
        if captured_my_piece:
            for board_str in self.boards:
                board = chess.Board(board_str)
                board.turn = not self.color  # simulate opponent move

                for move in self._generate_rbc_legal_moves(board):
                    
        # case 2: no piece was captured
        # find all moves that result in no capture
        # generate new boards from those moves
        else:
            for board_str in self.boards:
                board = chess.Board(board_str)
                board.turn = not self.color  # simulate opponent move

                for move in self._generate_rbc_legal_moves(board):
                    


        # limit the number of board states to 10,000 for performance reasons
        if len(new_boards) > 10000:
            before = len(new_boards)
            new_boards = set(random.sample(list(new_boards), 10000))
            after = len(new_boards)
            print(f"[DEBUG] Limited boards to 10 000: {before} -> {after}")

        print(f"[DEBUG] Boards expanded after opponent move: {len(self.boards)} -> {len(new_boards)}")

        # update the internal board states
        self.boards = new_boards

    def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> Square:
        # randomly select a sensing move from squares that are not on the edge of the board
        SEARCH_SPOTS = [
            9, 10, 11, 12, 13, 14,
            17, 18, 19, 20, 21, 22,
            25, 26, 27, 28, 29, 30,
            33, 34, 35, 36, 37, 38,
            41, 42, 43, 44, 45, 46,
            49, 50, 51, 52, 53, 54,
        ]
        choice = random.choice(SEARCH_SPOTS)
        print(f"[DEBUG] Chose sense square: {choice} ({chess.square_name(choice)})")
        return choice

    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):
        # filter possible board states based on the sense result
        before = len(self.boards)
        self.boards = self._filter_boards_by_sense_result(sense_result)
        after = len(self.boards)
        print(f"[DEBUG] Filtered boards by sense: {before} -> {after}.")

    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        print(f"[DEBUG] Choosing move. Boards: {len(self.boards)}, Move actions: {len(move_actions)}")

        if not self.boards or not move_actions:
            return None

        N = len(self.boards)
        time_per_board = 10.0 / N  # stockfish gets 10/N seconds per board
        move_votes = Counter()

        # iterate through possible states
        for board_str in self.boards:
            board = chess.Board(board_str)
            enemy_king = board.king(not self.color)
            move_found = False

            # first check for a king capture move
            if enemy_king is not None:
                for attacker in board.attackers(self.color, enemy_king):
                    move = chess.Move(attacker, enemy_king)
                    if move in move_actions:
                        move_votes[move.uci()] += 1
                        move_found = True
                        break

            # if no king capture found, ask Stockfish
            if not move_found:
                try:
                    move = self.engine.play(board, chess.engine.Limit(time=time_per_board)).move
                    if move in move_actions:
                        move_votes[move.uci()] += 1
                except Exception as e:
                    pass

        # decide the most common move
        if move_votes:
            best_moves = move_votes.most_common()
            max_votes = best_moves[0][1]
            top_moves = sorted([m for m, v in best_moves if v == max_votes])
            chosen = top_moves[0]
            print(f"[DEBUG] Selected move by vote: {chosen} with {max_votes} votes")
            return chess.Move.from_uci(chosen)

        # fallback: random legal move if nothing selected
        fallback = random.choice(move_actions)
        print(f"[DEBUG] Fallback random move: {fallback}")
        return fallback

    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move], captured_opponent_piece: bool, capture_square: Optional[Square]):
        # update possible board states based on the outcome of the move, if the move was taken
        print(f"[DEBUG] Move result. Requested: {requested_move}, Taken: {taken_move}, Captured: {captured_opponent_piece}, Capture square: {capture_square}")
        before = len(self.boards)
        self.boards = self._filter_boards_by_own_move_result(requested_move, taken_move)
        after = len(self.boards)
        print(f"[DEBUG] Filtered boards by own move result: {before} -> {after}")

    def handle_game_end(self, winner_color: Optional[Color], win_reason: Optional[WinReason], game_history: GameHistory):
        try:
            self.engine.quit()
            print("[DEBUG] Engine shut down")
        except chess.engine.EngineTerminatedError:
            pass

    # ==== Helpers ====

    def _generate_rbc_legal_moves(self, board: chess.Board) -> List[chess.Move]:
        moves = list(board.pseudo_legal_moves)
        moves.append(chess.Move.null())
        for move in reconchess.utilities.without_opponent_pieces(board).generate_castling_moves():
            if not reconchess.utilities.is_illegal_castle(board, move):
                moves.append(move)
        return moves

    def _filter_boards_by_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]) -> Set[str]:
        filtered = set()
        for board_str in self.boards:
            board = chess.Board(board_str)
            match = True
            for square, expected_piece in sense_result:
                actual_piece = board.piece_at(square)
                if actual_piece != expected_piece:
                    match = False
                    break
            if match:
                filtered.add(board_str)
        return filtered

    def _is_rbc_modified_move(self, board: chess.Board, requested: Optional[chess.Move], taken: Optional[chess.Move]) -> bool:
        if requested is None or taken is None:
            return False

        piece = board.piece_at(requested.from_square)
        if piece is None:
            return False

        # 1) Sliding piece modification (queen, rook, bishop)
        if piece.piece_type in [chess.ROOK, chess.BISHOP, chess.QUEEN]:
            if requested.from_square != taken.from_square:
                return False

            dx = chess.square_file(requested.to_square) - chess.square_file(requested.from_square)
            dy = chess.square_rank(requested.to_square) - chess.square_rank(requested.from_square)

            step_file = (dx > 0) - (dx < 0)
            step_rank = (dy > 0) - (dy < 0)

            file = chess.square_file(requested.from_square)
            rank = chess.square_rank(requested.from_square)

            while True:
                file += step_file
                rank += step_rank
                if not (0 <= file < 8 and 0 <= rank < 8):
                    break
                current = chess.square(file, rank)
                blocker = board.piece_at(current)
                if blocker:
                    # Check if first blocker is opponent piece and matches taken.to_square
                    if blocker.color != board.turn and current == taken.to_square:
                        return True
                    break
                if current == requested.to_square:
                    break
            return False

        # 2) Pawn double-step fallback
        elif piece.piece_type == chess.PAWN:
            # Pawn double move requested?
            start_rank = 1 if piece.color == chess.WHITE else 6
            from_rank = chess.square_rank(requested.from_square)
            to_rank = chess.square_rank(requested.to_square)
            if from_rank == start_rank and abs(to_rank - from_rank) == 2:
                # If requested is two-step, taken might be one-step forward
                one_step_rank = from_rank + (1 if piece.color == chess.WHITE else -1)
                one_step_sq = chess.square(chess.square_file(requested.from_square), one_step_rank)
                if taken.from_square == requested.from_square and taken.to_square == one_step_sq:
                    # Check that one-step move is legal (no opponent piece blocking)
                    temp_board = board.copy()
                    try:
                        temp_board.push(taken)
                        return True
                    except:
                        pass
            return False

        return False

    def _filter_boards_by_own_move_result(self, requested: Optional[chess.Move], taken: Optional[chess.Move]) -> Set[str]:
        filtered = set()

        # --- Case 1 ---
        # No move was taken => requested move must have been illegal
        # keep the boards where the requested move is illegal
        if taken is None:
            for board_str in self.boards:
                board = chess.Board(board_str)
                rbc_legal_moves = self._generate_rbc_legal_moves(board)
                if requested not in rbc_legal_moves:
                    filtered.add(board_str)

            return filtered

        # --- Case 2 ---
        # A move was taken, but it wasn't the move that was requested => move was modified
        # keep the boards where the requested move is legal and taken move was modified
        if requested != taken:
            print("[DEBUG] Requested move was modified.")
            for board_str in self.boards:
                board = chess.Board(board_str)
                rbc_legal_moves = self._generate_rbc_legal_moves(board)
                move_was_modified = self._is_rbc_modified_move(board, requested, taken)
                if requested in rbc_legal_moves and move_was_modified:
                    filtered.add(board_str)

            return filtered

        # --- Case 3 ---
        # Requested move was taken exactly => move was not modified
        # keep the boards where requested move is legal and taken move was not modified
        if requested == taken:
            print("[DEBUG] Requested move succeeded.")
            for board_str in self.boards:
                board = chess.Board(board_str)
                rbc_legal_moves = self._generate_rbc_legal_moves(board)
                move_was_modified = self._is_rbc_modified_move(board, requested, taken)
                if requested in rbc_legal_moves and not move_was_modified:
                    filtered.add(board_str)

            return filtered
        


        

