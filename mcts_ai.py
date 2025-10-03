# mcts_ai.py
import math
import random
import time
from collections import defaultdict
from gomoku_game import AI_PLAYER, HUMAN_PLAYER


class MCTSNode:
    # ... (This class is unchanged)
    def __init__(self, game_state, parent=None, move=None):
        self.game_state = game_state;
        self.parent = parent;
        self.move = move
        self.children = [];
        self.wins = 0;
        self.visits = 0
        self.untried_moves = self.game_state.get_legal_moves()

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
            'win': 1000000, 'block_win': 500000,
            'open_four': 10000, 'block_open_four': 5000,
            'closed_four': 5000, 'block_closed_four': 2500,
            'open_three': 1000, 'block_open_three': 500,
            'dev_own': 2, 'dev_opp': 1
        }

    def _score_move(self, game_state, move, player):
        """Final, robust scoring function."""
        opponent = HUMAN_PLAYER if player == AI_PLAYER else AI_PLAYER
        size = game_state.size
        score = 0

        # --- Priority 1 & 2: Check for immediate win or to block an opponent's win ---
        temp_game_win = game_state.clone();
        temp_game_win.make_move(move, player)
        if temp_game_win.check_winner() == player: return self.pattern_scores['win']

        temp_game_block = game_state.clone();
        temp_game_block.make_move(move, opponent)
        if temp_game_block.check_winner() == opponent: score += self.pattern_scores['block_win']

        # --- Check patterns this move would contribute to on the board ---
        # We check the board state *after* the move is made
        board_after_move = list(game_state.board);
        board_after_move[move] = player

        # My offensive patterns
        score += self._count_patterns_on_board(board_after_move, move, player, size, f" {player * 4} ",
                                               self.pattern_scores['open_four'])
        score += self._count_patterns_on_board(board_after_move, move, player, size, f" {player * 3} ",
                                               self.pattern_scores['open_three'])

        # My defensive patterns (blocking)
        # We need to check what threats the opponent has that this move neutralizes
        score += self._count_patterns_on_board(game_state.board, move, opponent, size, f" {opponent * 4} ",
                                               self.pattern_scores['block_open_four'])
        score += self._count_patterns_on_board(game_state.board, move, opponent, size, f" {opponent * 3} ",
                                               self.pattern_scores['block_open_three'])
        score += self._count_patterns_on_board(game_state.board, move, opponent, size,
                                               f" {opponent}{opponent} {opponent}{opponent} ",
                                               self.pattern_scores['block_closed_four'])

        # Add small score for development (playing near existing stones)
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
        """Checks how many times a pattern appears involving a specific move location."""
        r, c = divmod(move, size);
        total_score = 0
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            line = ""
            for i in range(-4, 5):
                nr, nc = r + i * dr, c + i * dc
                if 0 <= nr < size and 0 <= nc < size:
                    line += board[nr * size + nc]
                else:
                    line += "#"
            if pattern in line:
                total_score += score_value
        return total_score

    def _playout(self, game_state):
        """FAST playout heuristic. Uses only "local moves" to be quick."""
        # ... (This function is unchanged)
        legal_moves = game_state.get_legal_moves();
        if not legal_moves: return None
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
                    if 0 <= nr < size and 0 <= nc < size:
                        n_move = nr * size + nc
                        if game_state.board[n_move] == ' ': local_moves.add(n_move)
        return random.choice(list(local_moves)) if local_moves else random.choice(legal_moves)

    def find_best_move(self, root_state, time_limit_ms):
        """Main AI function combining fast MCTS search with a powerful final evaluation."""
        # ... (This function is unchanged)
        if not any(s != ' ' for s in root_state.board):
            center = (root_state.size // 2) * root_state.size + (root_state.size // 2)
            dummy_node = MCTSNode(game_state=root_state);
            dummy_node.visits = 1
            return center, dummy_node
        root_node = MCTSNode(game_state=root_state)
        start_time = time.monotonic()
        time_limit_secs = time_limit_ms / 1000.0
        while (time.monotonic() - start_time) < time_limit_secs:
            node = root_node;
            state = root_state.clone()
            while not node.untried_moves and node.children:
                node = max(node.children, key=lambda n: n.ucb1())
                state.make_move(node.move, state.current_player)
                state.current_player = HUMAN_PLAYER if state.current_player == AI_PLAYER else AI_PLAYER
            if node.untried_moves:
                move = random.choice(node.untried_moves)
                state.make_move(move, state.current_player)
                state.current_player = HUMAN_PLAYER if state.current_player == AI_PLAYER else AI_PLAYER
                node = node.add_child(move, state)
            current_rollout_state = state.clone()
            while current_rollout_state.check_winner() is None:
                possible_moves = current_rollout_state.get_legal_moves()
                if not possible_moves: break
                move = self._playout(current_rollout_state)
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
        top_candidates = sorted(root_node.children, key=lambda n: n.visits, reverse=True)[:10]
        best_score = -1
        best_move = top_candidates[0].move
        for candidate_node in top_candidates:
            move = candidate_node.move
            score = self._score_move(root_state, move, root_state.current_player)
            if score > best_score:
                best_score = score
                best_move = move
        return best_move, root_node