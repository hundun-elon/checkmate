import chess.engine
import reconchess
from reconchess import *
import random, math
from typing import Optional, List, Tuple, Set, Dict
from collections import Counter

class ImprovedBot3(Player):
    def __init__(self):
        # set of possible board states
        self.boards: Set[str] = set()
        self.color = None
        self.turn_num = None

        self.recent_sense_history = []
        self.sense_history_with_weight = {}

        #print("[DEBUG] Bot initialised")

        self.engine = chess.engine.SimpleEngine.popen_uci('./engines/stockfish', setpgrp=True)
        #print("[DEBUG] Stockfish engine started")

    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        # add initial board state to set
        self.boards = {board.fen()}
        self.color = color
        self.turn_num = 0

        color_name = "White" if color else "Black"
        print(f"[DEBUG] Game started. Color: {color_name}, Opponent: {opponent_name}")

    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square]):
        self.turn_num += 1
        #print(f"[DEBUG] Opponent move result. Captured: {captured_my_piece}, Square: {capture_square}")

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
            #print(f"[DEBUG] Limited boards to 10 000: {before} -> {after}")

        #print(f"[DEBUG] Boards expanded after opponent move: {len(self.boards)} -> {len(new_boards)}")
        
        # update the internal board states
        self.boards = new_boards

    def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> Square:
    
        def square_entropy(square: Square) -> float:
            """Compute Shannon entropy for a single square."""
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
        
        def sense_window_entropy(center_square: Square) -> float:
            """Compute entropy for entire 3x3 sensing window."""
            center_rank, center_file = divmod(center_square, 8)
            total_entropy = 0.0
            squares_in_window = 0
            
            for dr in [-1, 0, 1]:
                for df in [-1, 0, 1]:
                    rank, file = center_rank + dr, center_file + df
                    if 0 <= rank < 8 and 0 <= file < 8:
                        square = rank * 8 + file
                        total_entropy += square_entropy(square)
                        squares_in_window += 1
            
            return total_entropy / squares_in_window if squares_in_window > 0 else 0.0
        
        def analyze_uncertainty_disagreement(square: Square) -> float:
            """Analyze disagreement about what pieces exist at sensing locations."""
            center_rank, center_file = divmod(square, 8)
            total_disagreement = 0.0
            squares_analyzed = 0
            
            # Check disagreement for each square in the 3x3 sensing window
            for dr in [-1, 0, 1]:
                for df in [-1, 0, 1]:
                    rank, file = center_rank + dr, center_file + df
                    if 0 <= rank < 8 and 0 <= file < 8:
                        sq = rank * 8 + file
                        squares_analyzed += 1
                        
                        # Count different possibilities for this square
                        piece_possibilities = Counter()
                        for board_str in self.boards:
                            board = chess.Board(board_str)
                            piece = board.piece_at(sq)
                            piece_key = f"{piece.color}-{piece.piece_type}" if piece else "empty"
                            piece_possibilities[piece_key] += 1
                        
                        # Calculate disagreement for this square
                        if len(piece_possibilities) > 1:
                            total_count = sum(piece_possibilities.values())
                            # Use Gini impurity as disagreement measure
                            gini_impurity = 1.0 - sum((count/total_count)**2 for count in piece_possibilities.values())
                            total_disagreement += gini_impurity
            
            return total_disagreement / squares_analyzed if squares_analyzed > 0 else 0.0

        def get_strategic_zones() -> Dict[str, Set[Square]]:
            """Define strategic zones on the board."""
            return {
                'center': {chess.D4, chess.D5, chess.E4, chess.E5},
                'extended_center': {chess.C3, chess.C4, chess.C5, chess.C6,
                                chess.D3, chess.D4, chess.D5, chess.D6,
                                chess.E3, chess.E4, chess.E5, chess.E6,
                                chess.F3, chess.F4, chess.F5, chess.F6},
                'king_safety_white': {chess.F1, chess.G1, chess.H1, chess.F2, chess.G2, chess.H2},
                'king_safety_black': {chess.F8, chess.G8, chess.H8, chess.F7, chess.G7, chess.H7},
                'promotion_ranks': set(range(8)) | set(range(56, 64)),  # 1st and 8th ranks
            }
        
        def get_potential_moves_squares() -> Set[Square]:
            """Get squares that are potential move destinations with attack patterns."""
            move_squares = set()
            for move in move_actions:
                move_squares.add(move.to_square)
                
                # Add squares in attack patterns for pieces
                piece_type = None

                if len(self.boards) > 5:
                    boards_sample = set(random.sample(list(self.boards), 5))
                else:
                    boards_sample = self.boards

                for board_str in boards_sample:  # Sample a few boards for efficiency
                    board = chess.Board(board_str)
                    piece = board.piece_at(move.from_square)
                    if piece:
                        piece_type = piece.piece_type
                        break
                
                # Add relevant squares based on piece type
                if piece_type == chess.KNIGHT:
                    # Knight fork patterns
                    to_rank, to_file = divmod(move.to_square, 8)
                    knight_moves = [(-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)]
                    for dr, df in knight_moves:
                        new_rank, new_file = to_rank + dr, to_file + df
                        if 0 <= new_rank < 8 and 0 <= new_file < 8:
                            move_squares.add(new_rank * 8 + new_file)
                
                elif piece_type in [chess.ROOK, chess.QUEEN]:
                    # Add squares along ranks and files
                    to_rank, to_file = divmod(move.to_square, 8)
                    for i in range(8):
                        move_squares.add(to_rank * 8 + i)  # Same rank
                        move_squares.add(i * 8 + to_file)  # Same file
            
            return move_squares
        
        def analyze_threat_potential(square: Square) -> float:
            """Enhanced threat analysis with tactical patterns."""
            threat_score = 0.0
            
            for board_str in self.boards:
                board = chess.Board(board_str)
                piece = board.piece_at(square)
                
                if piece and piece.color != board.turn:  # Enemy piece
                    piece_values = {
                        chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                        chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 10  # King threats are critical
                    }
                    base_threat = piece_values.get(piece.piece_type, 0)
                    threat_score += base_threat
                    
                    # Bonus for pieces that can create forks/pins/skewers
                    if piece.piece_type in [chess.QUEEN, chess.ROOK, chess.BISHOP]:
                        threat_score += 2
                    elif piece.piece_type == chess.KNIGHT:
                        threat_score += 1.5  # Knights are good at forks
                    
                    # Bonus for advanced pieces
                    rank = square // 8
                    if piece.color == chess.BLACK and rank < 4:  # Black pieces advancing
                        threat_score += 1
                    elif piece.color == chess.WHITE and rank > 3:  # White pieces advancing
                        threat_score += 1
            
            return threat_score / len(self.boards)
        
        def analyze_board_reduction_potential(square: Square) -> float:
            """Estimate how much sensing this square will reduce board hypotheses."""
            piece_distributions = Counter()
            
            for board_str in self.boards:
                board = chess.Board(board_str)
                # Consider the 3x3 window around the sense square
                window_signature = []
                center_rank, center_file = divmod(square, 8)
                
                for dr in [-1, 0, 1]:
                    for df in [-1, 0, 1]:
                        rank, file = center_rank + dr, center_file + df
                        if 0 <= rank < 8 and 0 <= file < 8:
                            sq = rank * 8 + file
                            piece = board.piece_at(sq)
                            window_signature.append(str(piece) if piece else '.')
                
                piece_distributions[tuple(window_signature)] += 1
            
            # Calculate how evenly distributed the outcomes are
            total = len(self.boards)
            distribution_entropy = 0.0
            for count in piece_distributions.values():
                prob = count / total
                if prob > 0:
                    distribution_entropy += -prob * math.log2(prob)
            
            return distribution_entropy
        
        def get_game_phase_multipliers() -> Dict[str, float]:
            """Adjust priorities based on estimated game phase."""
            total_pieces = 0

            if len(self.boards) > 10:
                boards_sample = set(random.sample(list(self.boards), 10))
            else:
                boards_sample = self.boards

            for board_str in boards_sample:  # Sample for efficiency
                board = chess.Board(board_str)
                total_pieces += len([sq for sq in chess.SQUARES if board.piece_at(sq)])
            
            avg_pieces = total_pieces / min(10, len(self.boards))
            
            if avg_pieces > 24:  # Opening
                return {'center': 1.4, 'development': 1.3, 'king_safety': 1.1}
            elif avg_pieces > 16:  # Middlegame
                return {'center': 1.2, 'tactics': 1.4, 'king_safety': 1.2}
            else:  # Endgame
                return {'king_activity': 1.3, 'promotion': 1.4, 'center': 1.1}
        
        def update_sense_history(self, square: Square):
            """Track recently sensed squares with decay."""
            
            # Add current square with maximum weight
            self.sense_history_with_weight[square] = 1.0
            
            # Decay weights of previous senses
            for sq in list(self.sense_history_with_weight.keys()):
                self.sense_history_with_weight[sq] *= 0.7
                if self.sense_history_with_weight[sq] < 0.1:
                    del self.sense_history_with_weight[sq]
        
        def compute_advanced_score(square: Square) -> float:
            """Enhanced scoring with multiple factors."""
            # Base entropy (but consider full window)
            window_entropy = sense_window_entropy(square)
            single_entropy = square_entropy(square)
            entropy_score = 0.6 * window_entropy + 0.2 * single_entropy

            uncertainty_disagreement = analyze_uncertainty_disagreement(square)
            disagreement_score = 0.6 * uncertainty_disagreement
            
            # Board reduction potential
            reduction_score = analyze_board_reduction_potential(square)
            
            base_score = entropy_score + disagreement_score + 0.3 * reduction_score
            
            # Strategic zone bonuses
            zones = get_strategic_zones()
            game_phase = get_game_phase_multipliers()
            
            if square in zones['center']:
                base_score *= game_phase.get('center', 1.2)
            elif square in zones['extended_center']:
                base_score *= 1.1
            
            # Potential moves bonus
            potential_moves = get_potential_moves_squares()
            if square in potential_moves:
                base_score *= game_phase.get('tactics', 1.3)
            
            # Threat analysis
            threat_score = analyze_threat_potential(square)
            base_score += threat_score * 0.15
            
            # King safety
            if self.color == chess.WHITE and square in zones['king_safety_white']:
                base_score *= game_phase.get('king_safety', 1.15)
            elif self.color == chess.BLACK and square in zones['king_safety_black']:
                base_score *= game_phase.get('king_safety', 1.15)
            
            # Promotion rank bonus in endgame
            if square in zones['promotion_ranks']:
                base_score *= game_phase.get('promotion', 1.0)
            
            # Penalize recently sensed squares with decay
            if square in self.sense_history_with_weight:
                penalty = self.sense_history_with_weight[square]
                base_score *= (1.0 - 0.4 * penalty)
            
            # Bonus for squares that haven't been sensed recently
            if square not in self.sense_history_with_weight:
                base_score *= 1.1
            
            return base_score
        
        filtered_actions = [
            9, 10, 11, 12, 13, 14,
            17, 18, 19, 20, 21, 22,
            25, 26, 27, 28, 29, 30,
            33, 34, 35, 36, 37, 38,
            41, 42, 43, 44, 45, 46,
            49, 50, 51, 52, 53, 54,
        ]

        # Adaptive strategy based on board hypothesis count
        if len(self.boards) < 5:
            # Very few hypotheses - focus on window entropy
            best_square = max(filtered_actions, key=sense_window_entropy)
        elif len(self.boards) < 20:
            # Moderate hypotheses - balance entropy and strategy
            best_square = max(filtered_actions, 
                            key=lambda sq: 0.6 * square_entropy(sq) + 0.4 * compute_advanced_score(sq))
        else:
            # Many hypotheses - use full advanced scoring
            best_square = max(filtered_actions, key=compute_advanced_score)
        
        # Update history
        update_sense_history(self, best_square)
        
        # Enhanced debug information
        # entropy_val = square_entropy(best_square)
        # window_entropy_val = sense_window_entropy(best_square)
        # advanced_score = compute_advanced_score(best_square)
        # reduction_potential = analyze_board_reduction_potential(best_square)
        
        # print(f"[DEBUG] Chose sense square: {best_square} ({chess.square_name(best_square)})")
        # print(f"[DEBUG] Single entropy: {entropy_val:.3f}, Window entropy: {window_entropy_val:.3f}")
        # print(f"[DEBUG] Advanced score: {advanced_score:.3f}, Reduction potential: {reduction_potential:.3f}")
        # print(f"[DEBUG] Board hypotheses: {len(self.boards)}, Time left: {seconds_left:.1f}s")
        
        return best_square

    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):
        # filter possible board states based on the sense result
        before = len(self.boards)
        new_boards = self._filter_boards_by_sense_result(sense_result)
        after = len(new_boards)

        if len(new_boards) == 0:
            #print(f"[DEBUG] Boards collapsed to 0, keeping original boards")
            return
        
        self.boards = self._filter_boards_by_sense_result(sense_result)       
        #print(f"[DEBUG] Filtered boards by sense: {before} -> {after}.")

    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        #print(f"[DEBUG] Choosing move. Boards: {len(self.boards)}, Move actions: {len(move_actions)}")

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
            #print(f"[DEBUG] Selected move by vote: {chosen} with {max_votes} votes")
            return chess.Move.from_uci(chosen)

        # fallback: random legal move if nothing selected
        fallback = random.choice(move_actions)
        #print(f"[DEBUG] Fallback random move: {fallback}")
        return fallback

    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move], captured_opponent_piece: bool, capture_square: Optional[Square]):
        #print(f"[DEBUG] Move result. Requested: {requested_move}, Taken: {taken_move}, Captured: {captured_opponent_piece}, Capture square: {capture_square}")
        
        before = len(self.boards)
        new_boards = self._filter_boards_by_own_move_result(requested_move, taken_move)
        after = len(new_boards)

        if len(new_boards) == 0:
            #print("[DEBUG] Boards collapsed to 0, keeping original boards")
            return

        self.boards = new_boards
        #print(f"[DEBUG] Boards after own move result: {before} -> {after}")

    def handle_game_end(self, winner_color: Optional[Color], win_reason: Optional[WinReason], game_history: GameHistory):
        try:
            self.engine.quit()
            #print("[DEBUG] Engine shut down")
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
            #print("[DEBUG] Requested move was revised.")
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
            #print("[DEBUG] Requested move succeeded.")
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