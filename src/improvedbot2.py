import chess.engine
import reconchess
from reconchess import *
import random, math
from typing import Optional, List, Tuple, Set, Dict
from collections import Counter, defaultdict

class ImprovedBot(Player):
    def __init__(self):
        # set of possible board states
        self.boards: Set[str] = set()
        self.color = None
        self.turn_num = None

        self.recent_sense_history = []

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

        # case 1: our piece was captured
        # find all opponent moves that result in a capture at the capture square and generate new boards from those moves
        if captured_my_piece:
            for board_str in self.boards:
                board = chess.Board(board_str)
                board.turn = not self.color  # simulate opponent move

                for move in self._generate_rbc_legal_moves(board):
                    # get the capture square of the move
                    move_capture_square = reconchess.utilities.capture_square_of_move(board, move)
                    
                    # check if this move captures at the specified capture square
                    if move_capture_square == capture_square:
                        # create a new board with this move applied
                        new_board = board.copy()
                        try:
                            # first try the standard chess push
                            new_board.push(move)
                        except chess.IllegalMoveError:
                            # revise move to make it compatible 
                            revised_move = reconchess.utilities.revise_move(new_board, move)
                            if revised_move:
                                new_board.push(revised_move)
                            else:
                                # skip this move if it can't be revised
                                continue
                        
                        new_board.turn = self.color
                        new_boards.add(new_board.fen())
                    
        # case 2: no piece was captured
        # find all moves that result in no capture and generate new boards from those moves
        else:
            for board_str in self.boards:
                board = chess.Board(board_str)
                board.turn = not self.color  # simulate opponent move

                for move in self._generate_rbc_legal_moves(board):
                    # check if this move doesn't capture any piece
                    move_capture_square = reconchess.utilities.capture_square_of_move(board, move)
                    
                    if move_capture_square is None:
                        # create a new board with this move applied
                        new_board = board.copy()
                        try:
                            # first try the standard chess push
                            new_board.push(move)
                        except chess.IllegalMoveError:
                            # revise move to make it compatible
                            revised_move = reconchess.utilities.revise_move(new_board, move)
                            if revised_move:
                                new_board.push(revised_move)
                            else:
                                # skip this move if it can't be revised
                                continue
                        
                        new_board.turn = self.color
                        new_boards.add(new_board.fen())

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

        def square_entropy(square: Square) -> float:
            piece_counts = Counter()
            for board_str in self.boards:
                board = chess.Board(board_str)
                piece = board.piece_at(square)
                piece_counts[piece] += 1
            total = sum(piece_counts.values())
            if total == 0:
                return 0.0
            probs = [count / total for count in piece_counts.values()]
            return -sum(p * math.log2(p) for p in probs if p > 0)

        def square_disagreement(square: Square) -> float:
            seen = set()
            for board_str in self.boards:
                board = chess.Board(board_str)
                seen.add(board.piece_at(square))
            return len(seen) / len(self.boards)

        def macro_entropy(center: Square) -> float:
            total = 0.0
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    f = chess.square_file(center) + dx
                    r = chess.square_rank(center) + dy
                    if 0 <= f < 8 and 0 <= r < 8:
                        sq = chess.square(f, r)
                        total += square_entropy(sq)
            return total

        def macro_disagreement(center: Square) -> float:
            total = 0.0
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    f = chess.square_file(center) + dx
                    r = chess.square_rank(center) + dy
                    if 0 <= f < 8 and 0 <= r < 8:
                        sq = chess.square(f, r)
                        total += square_disagreement(sq)
            return total

        def get_strategic_zones() -> Dict[str, Set[Square]]:
            return {
                'center': {chess.D4, chess.D5, chess.E4, chess.E5},
                'extended_center': set(sum([
                    [chess.square(f, r) for f in range(2, 6)] for r in range(2, 6)
                ], [])),
                'king_safety_white': {chess.F1, chess.G1, chess.H1, chess.F2, chess.G2, chess.H2},
                'king_safety_black': {chess.F8, chess.G8, chess.H8, chess.F7, chess.G7, chess.H7},
            }

        def get_potential_moves_squares() -> Set[Square]:
            move_squares = set()
            for move in move_actions:
                move_squares.add(move.to_square)
                to_rank, to_file = divmod(move.to_square, 8)
                for dr in [-1, 0, 1]:
                    for df in [-1, 0, 1]:
                        nr, nf = to_rank + dr, to_file + df
                        if 0 <= nr < 8 and 0 <= nf < 8:
                            move_squares.add(nr * 8 + nf)
            return move_squares

        def analyze_threat_potential(square: Square) -> float:
            threat_score = 0.0
            for board_str in self.boards:
                board = chess.Board(board_str)
                piece = board.piece_at(square)
                if piece and piece.color != board.turn:
                    piece_values = {
                        chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                        chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0
                    }
                    threat_score += piece_values.get(piece.piece_type, 0)
                    if piece.piece_type in [chess.QUEEN, chess.ROOK, chess.BISHOP]:
                        threat_score += 2
            return threat_score / len(self.boards)

        def infer_game_phase() -> str:
            avg_piece_count = sum(board_str.count('r') + board_str.count('n') +
                                board_str.count('b') + board_str.count('q') +
                                board_str.count('R') + board_str.count('N') +
                                board_str.count('B') + board_str.count('Q')
                                for board_str in self.boards) / len(self.boards)
            if avg_piece_count > 8:
                return 'opening'
            elif avg_piece_count > 4:
                return 'midgame'
            else:
                return 'endgame'

        def update_sense_history(self, square: Square):
            self.recent_sense_history.append(square)
            if len(self.recent_sense_history) > 5:
                self.recent_sense_history.pop(0)

        def compute_weighted_score(center: Square) -> float:
            zones = get_strategic_zones()
            potential_moves = get_potential_moves_squares()
            game_phase = infer_game_phase()

            entropy_score = macro_entropy(center)
            disagreement_score = macro_disagreement(center)

            score = entropy_score * 0.6 + disagreement_score * 0.4

            if center in zones['center']:
                score *= 1.3 if game_phase != 'endgame' else 1.1
            elif center in zones['extended_center']:
                score *= 1.1

            if center in potential_moves:
                score *= 1.2
            
            # Bonus for threat potential
            threat_score = analyze_threat_potential(center)
            score += threat_score * 0.1

            if self.color == chess.WHITE and center in zones['king_safety_white']:
                score *= 1.15
            elif self.color == chess.BLACK and center in zones['king_safety_black']:
                score *= 1.15

            if center in self.recent_sense_history[-3:]:
                score *= 0.7

            return score

        # If early in game (low hypotheses), rely more on entropy
        if len(self.boards) < 10:
            best_square = max(sense_actions, key=macro_entropy)
        else:
            best_square = max(sense_actions, key=compute_weighted_score)

        update_sense_history(self, best_square)

        print(f"[DEBUG] Chose sense square: {best_square} ({chess.square_name(best_square)})")
        print(f"[DEBUG] Macro Entropy: {macro_entropy(best_square):.3f}, Disagreement: {macro_disagreement(best_square):.3f}")
        print(f"[DEBUG] Hypotheses: {len(self.boards)}, Game Phase: {infer_game_phase()}")

        return best_square

    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):
        # filter possible board states based on the sense result
        before = len(self.boards)
        new_boards = self._filter_boards_by_sense_result(sense_result)
        after = len(new_boards)

        if len(new_boards) == 0:
            print(f"[DEBUG] Boards collapsed to 0, keeping original boards")
            return
        
        self.boards = self._filter_boards_by_sense_result(sense_result)       
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
        print(f"[DEBUG] Move result. Requested: {requested_move}, Taken: {taken_move}, Captured: {captured_opponent_piece}, Capture square: {capture_square}")
        
        before = len(self.boards)
        new_boards = self._filter_boards_by_own_move_result(requested_move, taken_move)
        after = len(new_boards)

        if len(new_boards) == 0:
            print("[DEBUG] Boards collapsed to 0, keeping original boards")
            return

        self.boards = new_boards
        print(f"[DEBUG] Boards after own move result: {before} -> {after}")

    def handle_game_end(self, winner_color: Optional[Color], win_reason: Optional[WinReason], game_history: GameHistory):
        try:
            self.engine.quit()
            print("[DEBUG] Engine shut down")
        except chess.engine.EngineTerminatedError:
            pass

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
            if all(board.piece_at(square) == piece for square, piece in sense_result):
                filtered.add(board_str)
        return filtered

    def _moves_equivalent_ignoring_promotion(self, m1, m2):
        return (
            m1.from_square == m2.from_square and
            m1.to_square == m2.to_square and
            (
                m1.promotion == m2.promotion or
                (m1.promotion is None or m2.promotion is None)
            )
        )

    def _filter_boards_by_own_move_result(self, requested: Optional[chess.Move], taken: Optional[chess.Move]) -> Set[str]:
        filtered = set()

        # --- case 1 ---
        # no move was taken => requested move must have been illegal
        # keep the boards where the requested move is illegal
        if taken is None:
            for board_str in self.boards:
                board = chess.Board(board_str)
                # check if the move is legal in RBC
                is_move_legal = False
                for move in self._generate_rbc_legal_moves(board):
                    if move == requested:
                        is_move_legal = True
                        # try to push the move to catch any legality issues
                        try:
                            revised_move = reconchess.utilities.revise_move(board, move)
                            if revised_move:
                                test_board = board.copy()
                                test_board.push(revised_move)
                            else:
                                is_move_legal = False
                        except chess.IllegalMoveError:
                            is_move_legal = False
                        break
                        
                if not is_move_legal:
                    filtered.add(board_str)

            return filtered

        # --- case 2 ---
        # a move was taken, but it wasn't the move that was requested => move was revised
        # keep the boards where the requested move is legal and taken move was revised
        if requested != taken:
            print("[DEBUG] Requested move was revised.")
            for board_str in self.boards:
                board = chess.Board(board_str)
                # use reconchess utilities to check if the move would be revised in this board state
                revised_move = reconchess.utilities.revise_move(board, requested)
                
                # check if the revised move matches the taken move

                # also: if the requested move is a promotion, no promotion piece is specified,
                # RBC assumes a queen promotion by default. As a result, the requested move
                # and the actual move taken will differ.

                if revised_move and self._moves_equivalent_ignoring_promotion(revised_move, taken):
                    # create new board with the taken move
                    try:
                        new_board = board.copy()
                        new_board.push(taken)
                        filtered.add(new_board.fen())
                    except chess.IllegalMoveError:
                        # this shouldn't happen if the move was properly revised
                        pass

            return filtered

        # --- case 3 ---
        # requested move was taken exactly => move was not modified
        # keep the boards where requested move is legal and taken move was not modified
        if requested == taken:
            print("[DEBUG] Requested move succeeded.")
            for board_str in self.boards:
                board = chess.Board(board_str)
                # use reconchess utilities to check if the move would NOT be modified
                revised_move = reconchess.utilities.revise_move(board, requested)
                
                # if the move would not be modified and matches the requested/taken move
                if revised_move == requested:
                    # create new board with the taken move
                    try:
                        new_board = board.copy()
                        new_board.push(taken)
                        filtered.add(new_board.fen())
                    except chess.IllegalMoveError:
                        # this shouldn't happen for a legal move
                        pass

            return filtered