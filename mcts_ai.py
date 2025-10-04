# mcts_ai.py
import math
import random
import time
from collections import defaultdict
from gomoku_game import AI_PLAYER, HUMAN_PLAYER


class MCTSNode:
    def __init__(self, game_state, parent=None, move=None):
        self.game_state = game_state;
        self.parent = parent;
        self.move = move
        self.children = [];
        self.wins = 0;
        self.visits = 0
        self.untried_moves = game_state.get_legal_moves()

    def ucb1(self, exploration_constant=1.41):
        if self.visits == 0: return float('inf')
        return (self.wins / self.visits) + exploration_constant * math.sqrt(math.log(self.parent.visits) / self.visits)

    def add_child(self, move, new_state):
        child = MCTSNode(game_state=new_state, parent=self, move=move)
        self.children.append(child);
        self.untried_moves.remove(move);
        return child


class MCTS_AI:
    def __init__(self, heuristic_method='pattern'):
        self.heuristic_method = heuristic_method
        self.pattern_scores = {
            'win': 1000000, 'block_win': 500000, 'open_four': 10000, 'block_open_four': 20000,
            'open_three': 5000, 'block_open_three': 50000, 'dev_own': 2, 'dev_opp': 1
        }

    def _score_move(self, game_state, move, player):
        opponent = HUMAN_PLAYER if player == AI_PLAYER else AI_PLAYER
        size = game_state.size
        score = 0
        
        # Check for immediate win
        temp_game_win = game_state.clone()
        temp_game_win.make_move(move, player)
        if temp_game_win.check_winner() == player: 
            return self.pattern_scores['win']
        
        # Check for blocking opponent win
        temp_game_block = game_state.clone()
        temp_game_block.make_move(move, opponent)
        if temp_game_block.check_winner() == opponent: 
            score += self.pattern_scores['block_win']
        
        # CRITICAL: Check if this move blocks existing threats on the board
        threat_moves = self._scan_for_existing_threats(game_state.board, opponent, size)
        if move in threat_moves:
            score += self.pattern_scores['block_open_three'] * 10  # Very high priority for blocking threats

        # Check if opponent's move would create open three threat
        if self._detect_open_three_threat(game_state.board, move, opponent, size):
            score += self.pattern_scores['block_open_three'] * 5  # High priority
        
        # Check if our move creates open three
        if self._detect_open_three_threat(game_state.board, move, player, size):
            score += self.pattern_scores['open_three']
        
        # Original pattern counting (keep for other patterns)
        board_after_move = list(game_state.board)
        board_after_move[move] = player
        score += self._count_patterns_on_board(board_after_move, move, player, size, f" {player * 4} ",
                                               self.pattern_scores['open_four'])
        
        # Development bonuses for adjacent moves
        r, c = divmod(move, size)
        for ro in [-1, 0, 1]:
            for co in [-1, 0, 1]:
                if ro == 0 and co == 0: continue
                nr, nc = r + ro, c + co
                if 0 <= nr < size and 0 <= nc < size:
                    neighbor = game_state.board[nr * size + nc]
                    if neighbor == player:
                        score += self.pattern_scores['dev_own']
                    elif neighbor == opponent:
                        score += self.pattern_scores['dev_opp']
        
        return score

    def _count_patterns_on_board(self, board, move, player, size, pattern, score_value):
        r, c = divmod(move, size);
        total_score = 0;
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            line = ""
            for i in range(-4, 5):
                nr, nc = r + i * dr, c + i * dc
                if 0 <= nr < size and 0 <= nc < size:
                    line += board[nr * size + nc]
                else:
                    line += "#"
            if pattern in line: total_score += score_value
        return total_score

    def _get_line_around_position(self, board, r, c, dr, dc, size, length):
        """Extract a line of specified length around a position."""
        line = ""
        start_offset = -(length // 2)
        for i in range(start_offset, start_offset + length):
            nr, nc = r + i * dr, c + i * dc
            if 0 <= nr < size and 0 <= nc < size:
                cell = board[nr * size + nc]
                line += str(cell) if cell != ' ' else '_'
            else:
                line += "#"
        return line

    def _has_dangerous_three_pattern(self, line, player):
        """Check if a line contains dangerous three patterns."""
        p = str(player)
        dangerous_patterns = [
            f"_{p}{p}{p}_",     # _XXX_
            f"_{p}{p}_{p}_",    # _XX_X_
            f"_{p}_{p}{p}_",    # _X_XX_
        ]
        
        for pattern in dangerous_patterns:
            if pattern in line:
                return True
        return False

    def _get_scored_moves(self, game_state):
        moves_with_scores = []
        for move in game_state.get_legal_moves():
            score = self._score_move(game_state, move, game_state.current_player)
            moves_with_scores.append((score, move))
        return sorted(moves_with_scores, key=lambda x: x[0], reverse=True)

    def _get_fast_playout_move(self, game_state):
        """A fast, lightweight heuristic for use inside simulations."""
        legal_moves = game_state.get_legal_moves()
        if not legal_moves: return None

        player = game_state.current_player
        opponent = HUMAN_PLAYER if player == AI_PLAYER else AI_PLAYER

        # Priority 1 & 2: Check for immediate win or block
        for move in legal_moves:
            win_check = game_state.clone();
            win_check.make_move(move, player)
            if win_check.check_winner() == player: return move
        for move in legal_moves:
            block_check = game_state.clone();
            block_check.make_move(move, opponent)
            if block_check.check_winner() == opponent: return move

        # Priority 3: Fallback to local moves
        occupied = {i for i, spot in enumerate(game_state.board) if spot != ' '}
        if not occupied: return random.choice(legal_moves)

        local_moves = set()
        size = game_state.size
        for move in occupied:
            r, c = divmod(move, size)
            for ro in [-1, 0, 1]:
                for co in [-1, 0, 1]:
                    if ro == 0 and co == 0: continue
                    nr, nc = r + ro, c + co
                    if 0 <= nr < size and 0 <= nc < size and game_state.board[nr * size + nc] == ' ':
                        local_moves.add(nr * size + nc)

        return random.choice(list(local_moves)) if local_moves else random.choice(legal_moves)

    def _scan_for_existing_threats(self, board, player, size):
        """Scan the entire board for existing threats that need to be blocked."""
        threat_moves = []
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for pos in range(size * size):
            if board[pos] != ' ':
                continue

            r, c = divmod(pos, size)

            for dr, dc in directions:
                # Check if placing a stone here would block a dangerous pattern
                if self._would_block_threat(board, r, c, dr, dc, player, size):
                    threat_moves.append(pos)
                    break

        return threat_moves

    def _would_block_threat(self, board, r, c, dr, dc, opponent, size):
        """Check if placing a stone at (r,c) would block an opponent threat."""
        # Look in both directions from this position
        for direction_multiplier in [1, -1]:
            actual_dr, actual_dc = dr * direction_multiplier, dc * direction_multiplier

            # Count consecutive opponent stones
            consecutive = 0
            open_ends = 0

            # Check one direction
            i = 1
            while i <= 4:
                nr, nc = r + i * actual_dr, c + i * actual_dc
                if 0 <= nr < size and 0 <= nc < size:
                    if board[nr * size + nc] == opponent:
                        consecutive += 1
                        i += 1
                    elif board[nr * size + nc] == ' ':
                        open_ends += 1
                        break
                    else:
                        break
                else:
                    break

            # Check opposite direction
            i = 1
            while i <= 4:
                nr, nc = r - i * actual_dr, c - i * actual_dc
                if 0 <= nr < size and 0 <= nc < size:
                    if board[nr * size + nc] == opponent:
                        consecutive += 1
                        i += 1
                    elif board[nr * size + nc] == ' ':
                        open_ends += 1
                        break
                    else:
                        break
                else:
                    break

            # If we have 2+ consecutive opponent stones with at least one open end, it's a threat
            if consecutive >= 2 and open_ends >= 1:
                return True

            # Special case: check for patterns like O_OO where placing here blocks a future threat
            if consecutive >= 1:
                line = self._get_line_for_threat_analysis(board, r, c, actual_dr, actual_dc, size)
                if self._has_blocking_value(line, opponent):
                    return True

        return False

    def _get_line_for_threat_analysis(self, board, r, c, dr, dc, size):
        """Get a line for threat analysis with current position marked as blocking."""
        line = ""
        for i in range(-3, 4):
            nr, nc = r + i * dr, c + i * dc
            if nr == r and nc == c:
                line += "B"  # Blocking position
            elif 0 <= nr < size and 0 <= nc < size:
                cell = board[nr * size + nc]
                line += str(cell) if cell != ' ' else '_'
            else:
                line += "#"
        return line

    def _has_blocking_value(self, line, opponent):
        """Check if blocking at this position prevents dangerous patterns."""
        opp = str(opponent)
        # Patterns that would be blocked by placing here (B = blocking position)
        dangerous_patterns = [
            f"_{opp}B{opp}_",     # _XBX_ -> blocks potential _XXX_
            f"_{opp}{opp}B_",     # _XXB_ -> blocks potential _XXX_
            f"_B{opp}{opp}_",     # _BXX_ -> blocks potential _XXX_
            f"{opp}B{opp}",       # XBX -> important intersection
            f"{opp}{opp}B",       # XXB -> blocks extension
            f"B{opp}{opp}",       # BXX -> blocks extension
        ]

        for pattern in dangerous_patterns:
            if pattern in line:
                return True
        return False

    def _detect_open_three_threat(self, board, move, player, size):
        """Detect if a move creates an open three threat (three in a row with open ends)."""
        r, c = divmod(move, size)
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        
        # Create a temporary board with the move applied
        temp_board = list(board)
        temp_board[move] = player
        
        for dr, dc in directions:
            # Check for open three patterns in this direction
            consecutive = 1  # Count the placed stone
            open_ends = 0
            
            # Count consecutive stones in positive direction
            i = 1
            while i <= 4:
                nr, nc = r + i * dr, c + i * dc
                if 0 <= nr < size and 0 <= nc < size:
                    if temp_board[nr * size + nc] == player:
                        consecutive += 1
                        i += 1
                    elif temp_board[nr * size + nc] == ' ':
                        open_ends += 1
                        break
                    else:
                        break
                else:
                    break
            
            # Count consecutive stones in negative direction
            i = 1
            while i <= 4:
                nr, nc = r - i * dr, c - i * dc
                if 0 <= nr < size and 0 <= nc < size:
                    if temp_board[nr * size + nc] == player:
                        consecutive += 1
                        i += 1
                    elif temp_board[nr * size + nc] == ' ':
                        open_ends += 1
                        break
                    else:
                        break
                else:
                    break
            
            # Check if this creates a dangerous open three
            if consecutive == 3 and open_ends == 2:
                return True
                
            # Also check for broken threes that could be dangerous
            if consecutive >= 2:
                # Look for patterns like X_XX or XX_X with open ends
                line = self._get_line_around_position(temp_board, r, c, dr, dc, size, 6)
                if self._has_dangerous_three_pattern(line, player):
                    return True
        
        return False

    def find_best_move(self, root_state, time_limit_ms):
        if not any(s != ' ' for s in root_state.board):
            center = (root_state.size // 2) * root_state.size + (root_state.size // 2)
            dummy_node = MCTSNode(game_state=root_state);
            dummy_node.visits = 1
            return center, dummy_node

        initial_scored_moves = self._get_scored_moves(root_state)
        if initial_scored_moves:
            best_initial_score, best_initial_move = initial_scored_moves[0]
            if best_initial_score >= self.pattern_scores['block_win']:
                dummy_node = MCTSNode(game_state=root_state);
                dummy_node.visits = 1
                child_node = dummy_node.add_child(best_initial_move, root_state);
                child_node.wins = 1;
                child_node.visits = 1
                return best_initial_move, dummy_node

        root_node = MCTSNode(game_state=root_state)
        start_time = time.monotonic()
        time_limit_secs = time_limit_ms / 1000.0
        while (time.monotonic() - start_time) < time_limit_secs:
            node = root_node;
            state = root_state.clone()

            while not node.untried_moves and node.children:
                node = max(node.children, key=lambda n: n.ucb1())
                state.make_move(node.move, state.current_player);
                state.current_player = HUMAN_PLAYER if state.current_player == AI_PLAYER else AI_PLAYER

            if node.untried_moves:
                scored_untried_moves = [(score, move) for score, move in initial_scored_moves if
                                        move in node.untried_moves]
                if scored_untried_moves:
                    top_moves = [move for score, move in scored_untried_moves[:5]]
                    move = random.choice(top_moves)
                else:
                    move = random.choice(node.untried_moves)
                state.make_move(move, state.current_player);
                state.current_player = HUMAN_PLAYER if state.current_player == AI_PLAYER else AI_PLAYER
                node = node.add_child(move, state)

            # --- SIMULATION with the NEW, FAST, and SMART lightweight heuristic ---
            current_rollout_state = state.clone()
            while current_rollout_state.check_winner() is None:
                move = self._get_fast_playout_move(current_rollout_state)
                if move is None: break
                current_rollout_state.make_move(move, current_rollout_state.current_player)
                current_rollout_state.current_player = HUMAN_PLAYER if current_rollout_state.current_player == AI_PLAYER else AI_PLAYER

            winner = current_rollout_state.check_winner()

            while node is not None:
                node.visits += 1
                if node.parent:
                    player_who_moved = node.parent.game_state.current_player
                    if winner == player_who_moved:
                        node.wins += 1
                    elif winner == 'draw':
                        node.wins += 0.5
                node = node.parent

        if not root_node.children: return random.choice(root_state.get_legal_moves()), root_node

        best_child = max(root_node.children, key=lambda n: n.visits)
        return best_child.move, root_node