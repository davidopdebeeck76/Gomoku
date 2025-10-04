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
        self._all_win_lines = self._generate_all_win_lines()

    def _generate_all_win_lines(self):
        lines = []
        for r in range(self.size):
            for c in range(self.size - self.win_len + 1):
                lines.append([r * self.size + c + i for i in range(self.win_len)])
        for c in range(self.size):
            for r in range(self.size - self.win_len + 1):
                lines.append([(r + i) * self.size + c for i in range(self.win_len)])
        for r in range(self.size - self.win_len + 1):
            for c in range(self.size - self.win_len + 1):
                lines.append([(r + i) * self.size + (c + i) for i in range(self.win_len)])
        for r in range(self.win_len - 1, self.size):
            for c in range(self.size - self.win_len + 1):
                lines.append([(r - i) * self.size + (c + i) for i in range(self.win_len)])
        return lines

    def is_unwinnable(self, player):
        opponent = HUMAN_PLAYER if player == AI_PLAYER else AI_PLAYER
        for line in self._all_win_lines:
            if not any(self.board[pos] == opponent for pos in line):
                return False
        return True

    def get_legal_moves(self):
        return [i for i, spot in enumerate(self.board) if spot == ' ']

    def make_move(self, move, player):
        self.board[move] = player
        self.last_move = move

    def clone(self):
        cloned_game = GomokuGame(self.board, self.current_player, self.size, self.win_len)
        cloned_game.last_move = self.last_move
        return cloned_game

    def check_winner(self, fast_check=False):
        if self.last_move != -1:
            player = self.board[self.last_move]
            x, y = self.last_move % self.size, self.last_move // self.size
            directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
            for dx, dy in directions:
                count = 1
                for i in range(1, self.win_len):
                    nx, ny = x + i * dx, y + i * dy
                    if 0 <= nx < self.size and 0 <= ny < self.size and self.board[ny * self.size + nx] == player: count += 1
                    else: break
                for i in range(1, self.win_len):
                    nx, ny = x - i * dx, y - i * dy
                    if 0 <= nx < self.size and 0 <= ny < self.size and self.board[ny * self.size + nx] == player: count += 1
                    else: break
                if count >= self.win_len:
                    return player

        if not self.get_legal_moves():
            return 'draw'

        if fast_check:
            return None

        if self.is_unwinnable(AI_PLAYER) and self.is_unwinnable(HUMAN_PLAYER):
            return 'draw'

        return None