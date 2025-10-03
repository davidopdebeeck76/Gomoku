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
            'win': 1000000, 'block_win': 500000, 'open_four': 10000, 'block_open_four': 5000,
            'closed_four': 5000, 'block_closed_four': 2500, 'open_three': 1000,
            'block_open_three': 500, 'dev_own': 2, 'dev_opp': 1
        }

    def _score_move(self, game_state, move, player):
        # ... (This function is unchanged)
        opponent = HUMAN_PLAYER if player == AI_PLAYER else AI_PLAYER;
        size = game_state.size;
        score = 0
        temp_game_win = game_state.clone();
        temp_game_win.make_move(move, player)
        if temp_game_win.check_winner() == player: return self.pattern_scores['win']
        temp_game_block = game_state.clone();
        temp_game_block.make_move(move, opponent)
        if temp_game_block.check_winner() == opponent: score += self.pattern_scores['block_win']
        board_after_move = list(game_state.board);
        board_after_move[move] = player
        score += self._count_patterns_on_board(board_after_move, move, player, size, f" {player * 4} ",
                                               self.pattern_scores['open_four'])
        score += self._count_patterns_on_board(game_state.board, move, opponent, size, f" {opponent * 3} ",
                                               self.pattern_scores['block_open_three'])
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
        # ... (This function is unchanged)
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
        # ... (This function is unchanged)
        moves_with_scores = []
        for move in game_state.get_legal_moves():
            score = self._score_move(game_state, move, game_state.current_player)
            moves_with_scores.append((score, move))
        return sorted(moves_with_scores, key=lambda x: x[0], reverse=True)

    def _get_lightweight_heuristic_move(self, game_state):
        """A fast heuristic for use inside simulations."""
        legal_moves = game_state.get_legal_moves()
        if not legal_moves: return None
        player = game_state.current_player
        opponent = HUMAN_PLAYER if player == AI_PLAYER else AI_PLAYER

        # Priority 1: Check for my own winning moves
        for move in legal_moves:
            temp_game = game_state.clone();
            temp_game.make_move(move, player)
            if temp_game.check_winner() == player: return move

        # Priority 2: Check for opponent's winning moves to block
        for move in legal_moves:
            temp_game = game_state.clone();
            temp_game.make_move(move, opponent)
            if temp_game.check_winner() == opponent: return move

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
                child_node = dummy_node.add_child(best_initial_move, root_state)
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
                state.make_move(node.move, state.current_player)
                state.current_player = HUMAN_PLAYER if state.current_player == AI_PLAYER else AI_PLAYER

            if node.untried_moves:
                scored_untried_moves = [(score, move) for score, move in initial_scored_moves if
                                        move in node.untried_moves]
                if scored_untried_moves:
                    top_moves = [move for score, move in scored_untried_moves[:5]]
                    move = random.choice(top_moves)
                else:
                    move = random.choice(node.untried_moves)
                state.make_move(move, state.current_player)
                state.current_player = HUMAN_PLAYER if state.current_player == AI_PLAYER else AI_PLAYER
                node = node.add_child(move, state)

            # --- SIMULATION with the NEW lightweight heuristic ---
            current_rollout_state = state.clone()
            while current_rollout_state.check_winner() is None:
                move = self._get_lightweight_heuristic_move(current_rollout_state)
                if move is None: break
                current_rollout_state.make_move(move, current_rollout_state.current_player)
                current_rollout_state.current_player = HUMAN_PLAYER if current_rollout_state.current_player == AI_PLAYER else AI_PLAYER

            winner = current_rollout_state.check_winner()

            # --- BACKPROPAGATION ---
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