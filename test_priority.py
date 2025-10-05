# quick test: ensure AI prioritizes its immediate win over blocking opponent open three
from gomoku_game import GomokuGame, AI_PLAYER, HUMAN_PLAYER
from mcts_ai import MCTS_AI

# 9x9 board default
size = 9
board = [' ' for _ in range(size * size)]

# Put AI (X) four in a row on row 4, columns 3..6 (0-based)
r = 4
for c in (3,4,5,6):
    board[r * size + c] = AI_PLAYER

# Put opponent (O) open three on row 2, columns 4..6, with empties at 3 and 7
r2 = 2
for c in (4,5,6):
    board[r2 * size + c] = HUMAN_PLAYER

# ensure empties around
# create game state with AI to move
game = GomokuGame(board=board, current_player=AI_PLAYER, size=size)

ai = MCTS_AI()
move, node = ai.find_best_move(game, time_limit_ms=200, min_simulations=1)
print('AI chose move:', move)
print('Winning spots should include indices:', r * size + 2, 'or', r * size + 7)
print('Is chosen move a winning move?', move in (r * size + 2, r * size + 7))

# Print a small ASCII board around the area for visual check
for rr in range(size):
    row = ''.join(board[rr*size:(rr+1)*size])
    print(f"{rr:02d}: {row}")

# If the AI returned a dummy node with a child (early found), show that
if node and node.children:
    print('Root children moves and visits:')
    for ch in node.children:
        print(' move', ch.move, 'visits', ch.visits, 'wins', ch.wins)

