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
        # Scores are carefully weighted for a powerful heuristic
        self.scores = {
            'FIVE': 10000000,
            'FOUR_OPEN': 100000,
            'FOUR_CLOSED': 5000,
            'THREE_OPEN': 1000,
            'THREE_CLOSED': 100,
            'TWO_OPEN': 10,
            'TWO_CLOSED': 5,
            'DEV': 1
        }

    def _evaluate_line(self, line, player):
        """A robust function to evaluate a line of stones and return a score."""
        opponent = HUMAN_PLAYER if player == AI_PLAYER else AI_PLAYER
        my_stones = line.count(player)
        opp_stones = line.count(opponent)
        empty = line.count(' ')

        # We must have enough stones and space for a potential threat
        if my_stones + empty < 5 or opp_stones + empty < 5: return 0

        # Win/Loss
        if my_stones == 5: return self.scores['FIVE']
        if opp_stones == 5: return -self.scores['FIVE']

        # 4-in-a-row threats
        if my_stones == 4 and empty == 1:
            # Open Four threat (if there's space on both ends) - massive score
            if line[0] == ' ' and line[-1] == ' ': return self.scores['FOUR_OPEN']
            return self.scores['FOUR_CLOSED']

        if opp_stones == 4 and empty == 1:
            # Block necessary! This is the most critical block
            if line[0] == ' ' or line[-1] == ' ': return -self.scores['FOUR_OPEN']
            return -self.scores['FOUR_CLOSED']

        # 3-in-a-row threats
        if my_stones == 3 and empty == 2:
            # Open Three (e.g., '_OOO_' or '_O_OO_' or 'OO_O_')
            if line[0] == ' ' and line[-1] == ' ': return self.scores['THREE_OPEN']
            return self.scores['THREE_CLOSED']  # Closed or semi-open

        if opp_stones == 3 and empty == 2:
            if line[0] == ' ' and line[-1] == ' ': return -self.scores['THREE_OPEN']
            return -self.scores['THREE_CLOSED']

        # 2-in-a-row development (just to encourage connection)
        if my_stones == 2 and empty >= 3:
            if line[0] == ' ' and line[-1] == ' ': return self.scores['TWO_OPEN']

        return 0

    def _score_board_state(self, game_state, player):
        """Evaluates the entire board from one player's perspective."""
        total_score = 0
        size = game_state.size
        board = game_state.board

        # Check all possible lines of 5
        for r in range(size):
            for c in range(size):
                # Horizontal
                if c <= size - 5:
                    line = board[r * size + c: r * size + c + 5]
                    total_score += self._evaluate_line(line, player)
                # Vertical
                if r <= size - 5:
                    line = [board[(r + i) * size + c] for i in range(5)]
                    total_score += self._evaluate_line(line, player)
                # Diagonal \
                if r <= size - 5 and c <= size - 5:
                    line = [board[(r + i) * size + (c + i)] for i in range(5)]
                    total_score += self._evaluate_line(line, player)
                # Diagonal /
                if r <= size - 5 and c >= 4:
                    line = [board[(r + i) * size + (c - i)] for i in range(5)]
                    total_score += self._evaluate_line(line, player)
        return total_score

    def find_best_move(self, root_state, time_limit_ms):
        if not any(s != ' ' for s in root_state.board):
            center = (root_state.size // 2) * root_state.size + (root_state.size // 2)
            return center, MCTSNode(game_state=root_state)

        # --- Priority 1: "No-Brainer" Check ---
        # Find any move that results in an immediate win for me or blocks an opponent's win
        best_move = None
        for move in root_state.get_legal_moves():
            # Check for my win
            my_win_state = root_state.clone();
            my_win_state.make_move(move, root_state.current_player)
            if my_win_state.check_winner() == root_state.current_player:
                return move, MCTSNode(game_state=root_state)
            # Check for opponent's win to block
            opp_win_state = root_state.clone();
            opp_win_state.make_move(move, HUMAN_PLAYER if root_state.current_player == AI_PLAYER else AI_PLAYER)
            if opp_win_state.check_winner() == (HUMAN_PLAYER if root_state.current_player == AI_PLAYER else AI_PLAYER):
                best_move = move  # This is the mandatory block
                break  # We must play this move

        if best_move is not None:
            return best_move, MCTSNode(game_state=root_state)

        # --- Priority 2: MCTS search with PURELY RANDOM playouts ---
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
                move = random.choice(node.untried_moves)
                state.make_move(move, state.current_player);
                state.current_player = HUMAN_PLAYER if state.current_player == AI_PLAYER else AI_PLAYER
                node = node.add_child(move, state)
            current_rollout_state = state.clone()
            while current_rollout_state.check_winner() is None:
                possible_moves = current_rollout_state.get_legal_moves()
                if not possible_moves: break
                current_rollout_state.make_move(random.choice(possible_moves), current_rollout_state.current_player)
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

        # --- Priority 3: Final Selection using powerful board evaluation on top MCTS candidates ---
        top_candidates = sorted(root_node.children, key=lambda n: n.visits, reverse=True)[:10]
        best_score = -math.inf
        best_move = top_candidates[0].move
        for candidate_node in top_candidates:
            temp_state = root_state.clone()
            temp_state.make_move(candidate_node.move, root_state.current_player)
            score = self._score_board_state(temp_state, root_state.current_player)
            if score > best_score:
                best_score = score
                best_move = candidate_node.move
        return best_move, root_node