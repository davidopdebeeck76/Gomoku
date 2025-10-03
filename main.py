# main.py
import tkinter as tk
from tkinter import ttk, messagebox, Toplevel, scrolledtext
import json
import threading
import random

from gomoku_game import GomokuGame, AI_PLAYER, HUMAN_PLAYER
from mcts_ai import MCTS_AI

# --- Constants ---
BOARD_SIZE = 9
CELL_SIZE = 50
PADDING = 25
STATS_FILE = 'stats.json'
LOG_FILE = 'last_game_log.json'  # New constant for the log file


class GomokuGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gomoku AI")
        self.resizable(False, False)

        self.game = None
        self.ai = None
        self.game_over = True
        self.game_log = []  # Initialize game log

        self.stats = self._load_stats()

        self._create_widgets()
        self.after(100, self._show_settings_dialog)

    def _load_stats(self):
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_stats(self):
        with open(STATS_FILE, 'w') as f:
            json.dump(self.stats, f, indent=4)

    def _save_log(self):  # New method to save the game log
        with open(LOG_FILE, 'w') as f:
            json.dump(self.game_log, f, indent=4)

    def _create_widgets(self):
        # ... (Main layout is the same) ...
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        board_frame = ttk.Frame(main_frame)
        board_frame.pack(side=tk.LEFT, padx=(0, 10))
        self.info_frame = ttk.Frame(main_frame, width=200)
        self.info_frame.pack(side=tk.RIGHT, fill=tk.Y)
        canvas_size = (BOARD_SIZE - 1) * CELL_SIZE + 2 * PADDING
        self.canvas = tk.Canvas(board_frame, width=canvas_size, height=canvas_size, bg='#d2b48c')
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_board_click)

        # --- Right Panel Widgets ---
        self.turn_label = ttk.Label(self.info_frame, text="Start a new game", font=("Arial", 12))
        self.turn_label.pack(pady=5)
        ttk.Label(self.info_frame, text="AI Analysis", font=("Arial", 14, "bold")).pack(pady=5)
        self.mcts_text = tk.Text(self.info_frame, height=15, width=30, state=tk.DISABLED, font=("Courier", 9))
        self.mcts_text.pack(pady=5)
        ttk.Separator(self.info_frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Label(self.info_frame, text="Game Stats", font=("Arial", 14, "bold")).pack(pady=5)
        self.stats_text = tk.Text(self.info_frame, height=10, width=30, state=tk.DISABLED, font=("Courier", 9))
        self.stats_text.pack(pady=5)

        # --- Buttons Frame ---
        button_frame = ttk.Frame(self.info_frame)
        button_frame.pack(pady=10, fill='x')
        ttk.Button(button_frame, text="New Game", command=self._show_settings_dialog).pack(fill='x')
        # New button to view the log
        ttk.Button(button_frame, text="View Last Game Log", command=self._show_log_window).pack(fill='x', pady=(5, 0))

    def _show_settings_dialog(self):
        # ... (This function is unchanged)
        dialog = Toplevel(self);
        dialog.title("Game Settings");
        dialog.transient(self);
        dialog.grab_set()
        time_frame = ttk.Frame(dialog);
        time_frame.pack(padx=20, pady=(10, 5), fill='x')
        ttk.Label(time_frame, text="AI Thinking Time (seconds):").pack(anchor='w')
        time_var = tk.DoubleVar(value=3.0)
        time_label = ttk.Label(time_frame, text=f"{time_var.get():.1f} s");
        time_label.pack(side=tk.RIGHT, padx=(10, 0))

        def update_time_label(val): time_label.config(text=f"{float(val):.1f} s")

        time_slider = ttk.Scale(time_frame, from_=0.5, to=10.0, variable=time_var, orient='horizontal',
                                command=update_time_label);
        time_slider.pack(fill='x', expand=True)
        ttk.Label(dialog, text="AI Heuristic Method:").pack(padx=20, pady=(10, 5), anchor='w')
        heuristic_var = tk.StringVar(value='pattern')
        ttk.Radiobutton(dialog, text="Pattern-Based (Strongest)", variable=heuristic_var, value='pattern').pack(
            anchor='w', padx=20)
        ttk.Radiobutton(dialog, text="Pure Random (Weakest)", variable=heuristic_var, value='random').pack(anchor='w',
                                                                                                           padx=20)

        def on_start():
            self.settings = {'time_limit_ms': int(time_var.get() * 1000), 'heuristic': heuristic_var.get()}
            dialog.destroy();
            self._start_new_game()

        ttk.Button(dialog, text="Start Game", command=on_start).pack(padx=20, pady=20)
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _start_new_game(self):
        self.game_log = []  # Reset the log for the new game
        first_player = random.choice([HUMAN_PLAYER, AI_PLAYER])
        self.game = GomokuGame(size=BOARD_SIZE, current_player=first_player)
        self.ai = MCTS_AI(heuristic_method=self.settings.get('heuristic', 'pattern'))
        self.game_over = False
        self._draw_board()
        self._update_stats_text()
        if first_player == HUMAN_PLAYER:
            self._update_mcts_text("New game started. Your turn.")
            self._update_turn_label()
        else:
            self._update_mcts_text("New game started. AI's turn.")
            self._update_turn_label()
            self.after(500, self._ai_turn)

    def _draw_board(self):
        # ... (This function is unchanged)
        self.canvas.delete("all")
        for i in range(BOARD_SIZE):
            x = PADDING + i * CELL_SIZE
            self.canvas.create_line(x, PADDING, x, PADDING + (BOARD_SIZE - 1) * CELL_SIZE, fill='black')
            self.canvas.create_line(PADDING, x, PADDING + (BOARD_SIZE - 1) * CELL_SIZE, x, fill='black')
        for i, player in enumerate(self.game.board):
            if player != ' ':
                row, col = divmod(i, BOARD_SIZE);
                x0 = PADDING + col * CELL_SIZE - CELL_SIZE // 2 + 2
                y0 = PADDING + row * CELL_SIZE - CELL_SIZE // 2 + 2;
                x1 = PADDING + col * CELL_SIZE + CELL_SIZE // 2 - 2
                y1 = PADDING + row * CELL_SIZE + CELL_SIZE // 2 - 2;
                color = 'black' if player == AI_PLAYER else 'white'
                self.canvas.create_oval(x0, y0, x1, y1, fill=color, outline='black')

    def _on_board_click(self, event):
        # ... (This function is unchanged)
        if self.game_over or self.game.current_player != HUMAN_PLAYER: return
        col = round((event.x - PADDING) / CELL_SIZE);
        row = round((event.y - PADDING) / CELL_SIZE)
        if 0 <= col < BOARD_SIZE and 0 <= row < BOARD_SIZE:
            move = row * BOARD_SIZE + col
            if move in self.game.get_legal_moves(): self._make_human_move(move)

    def _make_human_move(self, move):
        # Log the human's move
        self.game_log.append({
            "turn": len(self.game_log) + 1,
            "player": "Human",
            "move": move
        })
        self.game.make_move(move, HUMAN_PLAYER)
        self._draw_board()
        winner = self.game.check_winner()
        if winner:
            self._end_game(winner)
        else:
            self.game.current_player = AI_PLAYER; self._ai_turn()

    def _ai_turn(self):
        # ... (This function is unchanged)
        self._update_turn_label();
        self._update_mcts_text("AI is thinking...")
        thread = threading.Thread(target=self._ai_worker, daemon=True);
        thread.start()

    def _ai_worker(self):
        # ... (This function is unchanged)
        ai_move, root_node = self.ai.find_best_move(self.game.clone(), self.settings['time_limit_ms'])
        self.after(0, self._process_ai_move, ai_move, root_node)

    def _process_ai_move(self, move, root_node):
        # Log the AI's move and its analysis
        analysis_data = {
            "total_simulations": root_node.visits,
            "top_moves": []
        }
        children = sorted(root_node.children, key=lambda n: n.visits, reverse=True)[:10]
        for child in children:
            analysis_data["top_moves"].append({
                "move": child.move,
                "win_rate": (child.wins / child.visits * 100) if child.visits > 0 else 0,
                "visits": child.visits
            })
        self.game_log.append({
            "turn": len(self.game_log) + 1,
            "player": "AI",
            "move": move,
            "analysis": analysis_data
        })

        self.game.make_move(move, AI_PLAYER)
        self._draw_board()
        self._update_mcts_text_from_node(root_node)
        winner = self.game.check_winner()
        if winner:
            self._end_game(winner)
        else:
            self.game.current_player = HUMAN_PLAYER; self._update_turn_label()

    def _end_game(self, winner):
        self.game_over = True
        self._update_turn_label()
        if winner == 'draw':
            message = "It's a draw!"
        else:
            message = f"Player {winner} wins!"
        messagebox.showinfo("Game Over", message)

        self._save_log()  # Save the log at the end of the game

        time_key = str(self.settings.get('time_limit_ms', 3000) / 1000)
        if time_key not in self.stats: self.stats[time_key] = {'wins': 0, 'losses': 0, 'total': 0}
        self.stats[time_key]['total'] += 1
        if winner == HUMAN_PLAYER:
            self.stats[time_key]['losses'] += 1
        elif winner == AI_PLAYER:
            self.stats[time_key]['wins'] += 1
        self._save_stats();
        self._update_stats_text()

    def _update_turn_label(self):
        # ... (This function is unchanged)
        if not self.game_over:
            player = self.game.current_player;
            text = f"Turn: {'Human (O)' if player == HUMAN_PLAYER else 'AI (X)'}"
            self.turn_label.config(text=text)
        else:
            self.turn_label.config(text="Game Over")

    def _update_mcts_text(self, message):
        # ... (This function is unchanged)
        self.mcts_text.config(state=tk.NORMAL);
        self.mcts_text.delete(1.0, tk.END)
        self.mcts_text.insert(tk.END, message);
        self.mcts_text.config(state=tk.DISABLED)

    def _update_mcts_text_from_node(self, root_node):
        # ... (This function is unchanged)
        lines = [f"Simulations: {root_node.visits}\n"];
        lines.append(f"{'Move':<6}{'Win%':<8}{'Visits':<8}")
        lines.append("-" * 22)
        children = sorted(root_node.children, key=lambda n: n.visits, reverse=True)[:10]
        for child in children:
            win_rate = (child.wins / child.visits * 100) if child.visits > 0 else 0
            lines.append(f"{child.move:<6}{win_rate:<8.2f}{child.visits:<8}")
        self._update_mcts_text("\n".join(lines))

    def _update_stats_text(self):
        # ... (This function is unchanged)
        lines = [f"{'Time(s)':<8}{'Win%':<8}{'W/L/T':<10}"];
        lines.append("-" * 26)
        for time_key, data in sorted(self.stats.items(), key=lambda item: float(item[0])):
            win_rate = (data['wins'] / data['total'] * 100) if data['total'] > 0 else 0
            wlt = f"{data['wins']}/{data['losses']}/{data['total']}"
            lines.append(f"{float(time_key):<8.1f}{win_rate:<8.2f}{wlt:<10}")
        self.stats_text.config(state=tk.NORMAL);
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, "\n".join(lines));
        self.stats_text.config(state=tk.DISABLED)

    def _show_log_window(self):  # New method to display the log
        try:
            with open(LOG_FILE, 'r') as f:
                log_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            messagebox.showinfo("Log Viewer", "No game log found. Play a game to create one.")
            return

        dialog = Toplevel(self);
        dialog.title("Last Game Log");
        dialog.geometry("500x600")

        log_text_widget = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, font=("Courier", 10))
        log_text_widget.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        formatted_log = ""
        for entry in log_data:
            formatted_log += f"--- Turn {entry['turn']} ({entry['player']}) ---\n"
            formatted_log += f"Move Played: {entry['move']}\n"
            if entry['player'] == 'AI':
                formatted_log += "\n  AI Analysis:\n"
                analysis = entry.get('analysis', {})
                formatted_log += f"  Total Simulations: {analysis.get('total_simulations', 'N/A')}\n"
                formatted_log += f"  {'Move':<6}{'Win%':<10}{'Visits':<8}\n"
                formatted_log += f"  {'------':<6}{'------':<10}{'------':<8}\n"
                for move_data in analysis.get('top_moves', []):
                    win_rate_str = f"{move_data.get('win_rate', 0):.2f}"
                    formatted_log += f"  {move_data.get('move', ''):<6}{win_rate_str:<10}{move_data.get('visits', ''):<8}\n"
            formatted_log += "\n" + "=" * 40 + "\n\n"

        log_text_widget.insert(tk.END, formatted_log)
        log_text_widget.config(state=tk.DISABLED)


if __name__ == "__main__":
    app = GomokuGUI()
    app.mainloop()