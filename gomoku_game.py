# gomoku_game.py

# Player constants
AI_PLAYER = 'X'
HUMAN_PLAYER = 'O'


class GomokuGame:
    def __init__(self, board=None, current_player=HUMAN_PLAYER, size=9, win_len=5):
        self.size = size
        self.win_len = win_len
        self.board = [' ' for _ in range(size * size)] if board is None else list(board)
        self.current_player = current_player
        self.last_move = -1

    def get_legal_moves(self):
        return [i for i, spot in enumerate(self.board) if spot == ' ']

    def make_move(self, move, player):
        self.board[move] = player
        self.last_move = move

    def clone(self):
        cloned_game = GomokuGame(self.board, self.current_player, self.size, self.win_len)
        cloned_game.last_move = self.last_move
        return cloned_game

    def check_winner(self):
        # Optimization: A winner is not possible until at least (win_len * 2 - 1) moves have been played.
        moves_played = self.size * self.size - len(self.get_legal_moves())
        if self.last_move == -1 or moves_played < (self.win_len * 2 - 1):
            return None

        player = self.board[self.last_move]
        x, y = self.last_move % self.size, self.last_move // self.size
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]  # Horizontal, Vertical, Diagonal Down, Diagonal Up

        for dx, dy in directions:
            count = 1
            # Check in the positive direction
            for i in range(1, self.win_len):
                nx, ny = x + i * dx, y + i * dy
                if 0 <= nx < self.size and 0 <= ny < self.size and self.board[ny * self.size + nx] == player:
                    count += 1
                else:
                    break
            # Check in the negative direction
            for i in range(1, self.win_len):
                nx, ny = x - i * dx, y - i * dy
                if 0 <= nx < self.size and 0 <= ny < self.size and self.board[
                    ny * self.size + nx] == player:  # <-- THE FIX IS HERE
                    count += 1
                else:
                    break

            if count >= self.win_len:
                return player

        if not self.get_legal_moves():
            return 'draw'

        return None