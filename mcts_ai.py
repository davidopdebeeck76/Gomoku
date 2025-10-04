# mcts_ai.py
import math
import random
import time
from collections import defaultdict
from gomoku_game import AI_PLAYER, HUMAN_PLAYER


class MCTSNode:
    # ... (unchanged)
    def __init__(self, game_state, parent=None,
                 move=None): self.game_state = game_state; self.parent = parent; self.move = move; self.children = []; self.wins = 0; self.visits = 0; self.untried_moves = game_state.get_legal_moves()

    def ucb1(self, exploration_constant=1.41):
        if self.visits == 0: return float('inf')
        return (self.wins / self.visits) + exploration_constant * math.sqrt(math.log(self.parent.visits) / self.visits)

    def add_child(self, move, new_state):
        child = MCTSNode(game_state=new_state, parent=self, move=move);
        self.children.append(child);
        self.untried_moves.remove(move);
        return child


class MCTS_AI:
    def __init__(self, heuristic_method='pattern'):
        self.heuristic_method = heuristic_method
        self.pattern_scores = {'win': 1000000, 'block_win': 500000, 'open_four': 10000, 'block_open_four': 20000,
                               'open_three': 5000, 'block_open_three': 50000, 'dev_own': 2, 'dev_opp': 1}

    # --- Your Powerful Heuristic Functions (unchanged and correct) ---
    def _score_move(self, game_state, move, player):
        # ... (This is your powerful function, it is unchanged)
        opponent = HUMAN_PLAYER if player == AI_PLAYER else AI_PLAYER;
        size = game_state.size;
        score = 0
        temp_game_win = game_state.clone();
        temp_game_win.make_move(move, player)
        if temp_game_win.check_winner() == player: return self.pattern_scores['win']
        temp_game_block = game_state.clone();
        temp_game_block.make_move(move, opponent)
        if temp_game_block.check_winner() == opponent: score += self.pattern_scores['block_win']
        threat_moves = self._scan_for_existing_threats(game_state.board, opponent, size)
        if move in threat_moves: score += self.pattern_scores['block_open_three'] * 10
        if self._detect_open_three_threat(game_state.board, move, opponent, size): score += self.pattern_scores[
                                                                                                'block_open_three'] * 5
        if self._detect_open_three_threat(game_state.board, move, player, size): score += self.pattern_scores[
            'open_three']
        board_after_move = list(game_state.board);
        board_after_move[move] = player
        score += self._count_patterns_on_board(board_after_move, move, player, size, f" {player * 4} ",
                                               self.pattern_scores['open_four'])
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
        # ... (unchanged)
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

    def _get_scored_moves(self, game_state):
        # ... (unchanged)
        moves_with_scores = []
        for move in game_state.get_legal_moves():
            score = self._score_move(game_state, move, game_state.current_player)
            moves_with_scores.append((score, move))
        return sorted(moves_with_scores, key=lambda x: x[0], reverse=True)

    def _scan_for_existing_threats(self, board, player, size):
        # ... (unchanged)
        threat_moves = set();
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for pos in range(size * size):
            if board[pos] != player: continue
            r, c = divmod(pos, size)
            for dr, dc in directions:
                line_positions, line_chars = [], []
                for i in range(-2, 4):
                    nr, nc = r + i * dr, c + i * dc
                    if 0 <= nr < size and 0 <= nc < size:
                        line_positions.append(nr * size + nc);
                        cell = board[nr * size + nc];
                        line_chars.append('X' if cell == player else '_' if cell == ' ' else 'O')
                    else:
                        line_positions.append(None); line_chars.append('#')
                line_str = ''.join(line_chars)
                if '_XXX_' in line_str: idx = line_str.find('_XXX_'); threat_moves.add(
                    line_positions[idx]); threat_moves.add(line_positions[idx + 4])
                if '_XX_X_' in line_str: threat_moves.add(line_positions[line_str.find('_XX_X_') + 3])
                if '_X_XX_' in line_str: threat_moves.add(line_positions[line_str.find('_X_XX_') + 2])
                if 'XXXX' in line_str:
                    idx = line_str.find('XXXX')
                    if idx > 0 and line_chars[idx - 1] == '_': threat_moves.add(line_positions[idx - 1])
                    if idx + 4 < len(line_positions) and line_chars[idx + 4] == '_': threat_moves.add(
                        line_positions[idx + 4])
        return list(filter(None, threat_moves))

    def _detect_open_three_threat(self, board, move, player, size):
        # ... (unchanged)
        r, c = divmod(move, size);
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)];
        temp_board = list(board);
        temp_board[move] = player
        for dr, dc in directions:
            consecutive, open_ends = 1, 0
            for i in range(1, 5):
                nr, nc = r + i * dr, c + i * dc
                if 0 <= nr < size and 0 <= nc < size:
                    if temp_board[nr * size + nc] == player:
                        consecutive += 1
                    elif temp_board[nr * size + nc] == ' ':
                        open_ends += 1; break
                    else:
                        break
                else:
                    break
            for i in range(1, 5):
                nr, nc = r - i * dr, c - i * dc
                if 0 <= nr < size and 0 <= nc < size:
                    if temp_board[nr * size + nc] == player:
                        consecutive += 1
                    elif temp_board[nr * size + nc] == ' ':
                        open_ends += 1; break
                    else:
                        break
                else:
                    break
            if consecutive == 3 and open_ends == 2: return True
        return False

    # --- The Fix: A Dispatcher and a Renamed Smart Heuristic ---

    # NEW: This is the dispatcher function that will be called inside the simulation.
    def _playout(self, game_state):
        if self.heuristic_method == 'pattern':
            return self._get_smart_playout_move(game_state)
        else:  # 'random'
            return random.choice(game_state.get_legal_moves())

    # MODIFIED: Renamed from _get_fast_playout_move to be more specific.
    def _get_smart_playout_move(self, game_state):
        """A fast, lightweight heuristic for use inside simulations for 'Tony'."""
        legal_moves = game_state.get_legal_moves()
        if not legal_moves: return None

        player = game_state.current_player
        opponent = HUMAN_PLAYER if player == AI_PLAYER else AI_PLAYER

        for move in legal_moves:
            win_check = game_state.clone();
            win_check.make_move(move, player)
            if win_check.check_winner(fast_check=True) == player: return move
        for move in legal_moves:
            block_check = game_state.clone();
            block_check.make_move(move, opponent)
            if block_check.check_winner(fast_check=True) == opponent: return move

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

    def find_best_move(self, root_state, time_limit_ms, min_simulations):
        if not any(s != ' ' for s in root_state.board):
            center = (root_state.size // 2) * root_state.size + (root_state.size // 2);
            dummy_node = MCTSNode(game_state=root_state);
            dummy_node.visits = 1;
            return center, dummy_node

        initial_scored_moves = self._get_scored_moves(root_state)
        if initial_scored_moves:
            best_initial_score, best_initial_move = initial_scored_moves[0]
            if best_initial_score >= self.pattern_scores['block_win']:
                dummy_node = MCTSNode(game_state=root_state);
                dummy_node.visits = 1;
                child_node = dummy_node.add_child(best_initial_move, root_state);
                child_node.wins = 1;
                child_node.visits = 1;
                return best_initial_move, dummy_node

        root_node = MCTSNode(game_state=root_state);
        start_time = time.monotonic();
        time_limit_secs = time_limit_ms / 1000.0;
        simulations_run = 0
        while (time.monotonic() - start_time) < time_limit_secs or simulations_run < min_simulations:
            simulations_run += 1;
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
                    top_moves = [move for score, move in scored_untried_moves[:5]];
                    move = random.choice(top_moves)
                else:
                    move = random.choice(node.untried_moves)
                state.make_move(move, state.current_player);
                state.current_player = HUMAN_PLAYER if state.current_player == AI_PLAYER else AI_PLAYER;
                node = node.add_child(move, state)

            current_rollout_state = state.clone()
            while current_rollout_state.check_winner(fast_check=True) is None:
                # MODIFIED: Call the new dispatcher function
                move = self._playout(current_rollout_state)
                if move is None: break
                current_rollout_state.make_move(move, current_rollout_state.current_player)
                current_rollout_state.current_player = HUMAN_PLAYER if current_rollout_state.current_player == AI_PLAYER else AI_PLAYER
            winner = current_rollout_state.check_winner(fast_check=True)

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