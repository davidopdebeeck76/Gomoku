# main.py
import tkinter as tk
from tkinter import ttk, messagebox, Toplevel, scrolledtext
import json
import threading
import random
import queue

from gomoku_game import GomokuGame, AI_PLAYER, HUMAN_PLAYER
from mcts_ai import MCTS_AI

# --- Constants ---
BOARD_SIZE = 9
CELL_SIZE = 50
PADDING = 25
STATS_FILE = 'stats.json'
LOG_FILE = 'last_game_log.json'


class GomokuGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gomoku AI")
        self.resizable(False, False)

        self.game = None
        self.ai = None
        self.game_over = True
        self.game_log = []

        self.stats = self._load_stats()

        # Visualization state
        self.viz_enabled = False
        self.viz_queue = queue.Queue()
        self.viz_update_rate = 10  # Process every Nth iteration
        self.ghost_pieces = []  # Track canvas items for ghost pieces

        self._create_widgets()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Start visualization processing loop
        self._process_viz_queue()

        self.after(100, self._show_settings_dialog)

    def _on_closing(self):
        """Handle the window closing event to clean up resources."""
        # No pool to close in this architecture, just destroy.
        self.destroy()

    def _load_stats(self):
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_stats(self):
        with open(STATS_FILE, 'w') as f: json.dump(self.stats, f, indent=4)

    def _save_log(self):
        with open(LOG_FILE, 'w') as f: json.dump(self.game_log, f, indent=4)

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10);
        main_frame.pack(fill=tk.BOTH, expand=True)
        board_frame = ttk.Frame(main_frame);
        board_frame.pack(side=tk.LEFT, padx=(0, 10))
        self.info_frame = ttk.Frame(main_frame, width=200);
        self.info_frame.pack(side=tk.LEFT, fill=tk.Y)

        # Visualization panel
        self.viz_frame = ttk.Frame(main_frame, width=300)
        self.viz_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        canvas_size = (BOARD_SIZE - 1) * CELL_SIZE + 2 * PADDING
        self.canvas = tk.Canvas(board_frame, width=canvas_size, height=canvas_size, bg='#d2b48c');
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_board_click)
        self.turn_label = ttk.Label(self.info_frame, text="Start a new game", font=("Arial", 12));
        self.turn_label.pack(pady=5)
        ttk.Label(self.info_frame, text="AI Analysis", font=("Arial", 14, "bold")).pack(pady=5)
        self.mcts_text = tk.Text(self.info_frame, height=15, width=30, state=tk.DISABLED, font=("Courier", 9));
        self.mcts_text.pack(pady=5)
        ttk.Separator(self.info_frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Label(self.info_frame, text="Game Stats", font=("Arial", 14, "bold")).pack(pady=5)
        self.stats_text = tk.Text(self.info_frame, height=10, width=30, state=tk.DISABLED, font=("Courier", 9));
        self.stats_text.pack(pady=5)
        button_frame = ttk.Frame(self.info_frame);
        button_frame.pack(pady=10, fill='x')
        ttk.Button(button_frame, text="New Game", command=self._show_settings_dialog).pack(fill='x')
        ttk.Button(button_frame, text="View Last Game Log", command=self._show_log_window).pack(fill='x', pady=(5, 0))

        # --- Visualization Panel ---
        ttk.Label(self.viz_frame, text="MCTS Visualization", font=("Arial", 14, "bold")).pack(pady=5)

        # Visualization controls
        control_frame = ttk.Frame(self.viz_frame)
        control_frame.pack(fill='x', padx=5, pady=5)

        self.viz_enabled_var = tk.BooleanVar(value=False)
        viz_toggle = ttk.Checkbutton(control_frame, text="Enable Visualization",
                                       variable=self.viz_enabled_var,
                                       command=self._toggle_visualization)
        viz_toggle.pack(side=tk.LEFT, padx=5)

        ttk.Label(control_frame, text="Update Rate:").pack(side=tk.LEFT, padx=(10, 2))
        self.viz_rate_var = tk.StringVar(value="10")
        rate_spin = ttk.Spinbox(control_frame, from_=1, to=100, width=5,
                                 textvariable=self.viz_rate_var,
                                 command=self._update_viz_rate)
        rate_spin.pack(side=tk.LEFT)

        # Visualization text output with scrollbar
        viz_scroll_frame = ttk.Frame(self.viz_frame)
        viz_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(viz_scroll_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.viz_text = tk.Text(viz_scroll_frame, width=40, height=35,
                                 font=("Courier", 8), wrap=tk.WORD,
                                 yscrollcommand=scrollbar.set)
        self.viz_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.viz_text.yview)

        # Configure text tags for coloring
        self.viz_text.tag_config("phase", foreground="#0066cc", font=("Courier", 8, "bold"))
        self.viz_text.tag_config("selection", foreground="#009900")
        self.viz_text.tag_config("expansion", foreground="#cc6600")
        self.viz_text.tag_config("simulation", foreground="#9900cc")
        self.viz_text.tag_config("backprop", foreground="#cc0000")
        self.viz_text.tag_config("info", foreground="#666666")

        clear_btn = ttk.Button(self.viz_frame, text="Clear Visualization Log",
                               command=self._clear_viz_log)
        clear_btn.pack(pady=5)

    def _show_settings_dialog(self):
        dialog = Toplevel(self);
        dialog.title("Game Settings");
        dialog.transient(self);
        dialog.grab_set()

        settings_frame = ttk.Frame(dialog, padding=20)
        settings_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(settings_frame, text="Time Limit (ms):").grid(row=0, column=0, sticky='w', pady=5)
        time_var = tk.StringVar(value="3000")
        ttk.Entry(settings_frame, textvariable=time_var, width=10).grid(row=0, column=1, sticky='e')

        ttk.Label(settings_frame, text="Min. Simulations:").grid(row=1, column=0, sticky='w', pady=5)
        sims_var = tk.StringVar(value="1000")
        ttk.Entry(settings_frame, textvariable=sims_var, width=10).grid(row=1, column=1, sticky='e')

        ttk.Label(dialog, text="AI Difficulty Level:").pack(padx=20, pady=(10, 5), anchor='w')
        heuristic_var = tk.StringVar(value='pattern')
        ttk.Radiobutton(dialog, text="Dim Opponent", variable=heuristic_var, value='pattern').pack(anchor='w', padx=20)
        ttk.Radiobutton(dialog, text="Goldfish", variable=heuristic_var, value='random').pack(anchor='w', padx=20)

        def on_start():
            try:
                time_limit = int(time_var.get())
                min_sims = int(sims_var.get())
                if time_limit < 100 or min_sims < 10:
                    raise ValueError("Values are too low.")
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numbers for time (>=100) and simulations (>=10).")
                return

            self.settings = {
                'time_limit_ms': time_limit,
                'min_simulations': min_sims,
                'heuristic': heuristic_var.get()
            }
            dialog.destroy();
            self._start_new_game()

        ttk.Button(dialog, text="Start Game", command=on_start).pack(padx=20, pady=20)
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2);
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _start_new_game(self):
        self.game_log = []
        first_player = random.choice([HUMAN_PLAYER, AI_PLAYER])
        self.game = GomokuGame(size=BOARD_SIZE, current_player=first_player)
        self.ai = MCTS_AI(heuristic_method=self.settings.get('heuristic', 'pattern'))

        # Set up visualization callback
        self.ai.visualization_callback = self._viz_callback
        self.ai.visualization_enabled = self.viz_enabled

        self.game_over = False;
        self._draw_board();
        self._update_stats_text()
        if first_player == HUMAN_PLAYER:
            self._update_mcts_text("New game started. Your turn.");
            self._update_turn_label()
        else:
            self._update_mcts_text("New game started. AI's turn.");
            self._update_turn_label()
            self.after(500, self._ai_turn)

    def _draw_board(self):
        self.canvas.delete("all")
        for i in range(BOARD_SIZE):
            x = PADDING + i * CELL_SIZE
            self.canvas.create_line(x, PADDING, x, PADDING + (BOARD_SIZE - 1) * CELL_SIZE, fill='black')
            self.canvas.create_line(PADDING, x, PADDING + (BOARD_SIZE - 1) * CELL_SIZE, x, fill='black')
        for i, player in enumerate(self.game.board):
            if player != ' ':
                row, col = divmod(i, BOARD_SIZE)
                x0 = PADDING + col * CELL_SIZE - CELL_SIZE // 2 + 2;
                y0 = PADDING + row * CELL_SIZE - CELL_SIZE // 2 + 2
                x1 = PADDING + col * CELL_SIZE + CELL_SIZE // 2 - 2;
                y1 = PADDING + row * CELL_SIZE + CELL_SIZE // 2 - 2
                color = 'black' if player == AI_PLAYER else 'white'
                self.canvas.create_oval(x0, y0, x1, y1, fill=color, outline='black')
                if i == self.game.last_move:
                    center_x = PADDING + col * CELL_SIZE;
                    center_y = PADDING + row * CELL_SIZE
                    dot_radius = CELL_SIZE // 8
                    dot_x0, dot_y0 = center_x - dot_radius, center_y - dot_radius
                    dot_x1, dot_y1 = center_x + dot_radius, center_y + dot_radius
                    highlight_color = 'white' if player == AI_PLAYER else 'black'
                    self.canvas.create_oval(dot_x0, dot_y0, dot_x1, dot_y1, fill=highlight_color, outline="")

    def _on_board_click(self, event):
        if self.game_over or self.game.current_player != HUMAN_PLAYER: return
        col = round((event.x - PADDING) / CELL_SIZE);
        row = round((event.y - PADDING) / CELL_SIZE)
        if 0 <= col < BOARD_SIZE and 0 <= row < BOARD_SIZE:
            move = row * BOARD_SIZE + col
            if move in self.game.get_legal_moves(): self._make_human_move(move)

    def _make_human_move(self, move):
        self.game_log.append({"turn": len(self.game_log) + 1, "player": "Human", "move": move})
        self.game.make_move(move, HUMAN_PLAYER);
        self._draw_board()
        self.update_idletasks()  # Force immediate drawing of human move
        winner = self.game.check_winner()
        if winner:
            self._end_game(winner)
        else:
            self.game.current_player = AI_PLAYER;
            self.after(10, self._ai_turn)  # Small delay to ensure UI updates

    def _ai_turn(self):
        self._update_turn_label();
        self._update_mcts_text("AI is thinking...")
        self._clear_ghost_pieces()  # Clear any lingering ghost pieces
        self.update_idletasks()  # Force UI update before AI starts
        thread = threading.Thread(target=self._ai_worker, daemon=True);
        thread.start()

    def _ai_worker(self):
        ai_move, root_node = self.ai.find_best_move(
            self.game.clone(),
            self.settings['time_limit_ms'],
            self.settings['min_simulations']
        )
        self.after(0, self._process_ai_move, ai_move, root_node)

    def _process_ai_move(self, move, root_node):
        analysis_data = {"total_simulations": root_node.visits, "top_moves": []}
        children = sorted(root_node.children, key=lambda n: n.visits, reverse=True)[:10]
        for child in children:
            analysis_data["top_moves"].append({"move": child.move, "win_rate": (child.wins / child.visits * 100) if child.visits > 0 else 0, "visits": child.visits})
        self.game_log.append({"turn": len(self.game_log) + 1, "player": "AI", "move": move, "analysis": analysis_data})
        self.game.make_move(move, AI_PLAYER);
        self._draw_board();
        self._update_mcts_text_from_node(root_node)
        winner = self.game.check_winner()
        if winner:
            self._end_game(winner)
        else:
            self.game.current_player = HUMAN_PLAYER;
            self._update_turn_label()

    def _end_game(self, winner):
        self.game_over = True;
        self._update_turn_label()
        if winner == 'draw':
            message = "It's a draw!"
        else:
            message = f"Player {winner} wins!"
        messagebox.showinfo("Game Over", message);
        self._save_log()
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
        if not self.game_over:
            player = self.game.current_player;
            text = f"Turn: {'Human (O)' if player == HUMAN_PLAYER else 'AI (X)'}"
            self.turn_label.config(text=text)
        else:
            self.turn_label.config(text="Game Over")

    def _update_mcts_text(self, message):
        self.mcts_text.config(state=tk.NORMAL);
        self.mcts_text.delete(1.0, tk.END)
        self.mcts_text.insert(tk.END, message);
        self.mcts_text.config(state=tk.DISABLED)

    def _update_mcts_text_from_node(self, root_node):
        lines = [f"Simulations: {root_node.visits}\n"];
        lines.append(f"{'Move':<6}{'Win%':<8}{'Visits':<8}")
        lines.append("-" * 22)
        children = sorted(root_node.children, key=lambda n: n.visits, reverse=True)[:10]
        for child in children:
            win_rate = (child.wins / child.visits * 100) if child.visits > 0 else 0
            lines.append(f"{child.move:<6}{win_rate:<8.2f}{child.visits:<8}")
        self._update_mcts_text("\n".join(lines))

    def _update_stats_text(self):
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

    def _show_log_window(self):
        try:
            with open(LOG_FILE, 'r') as f:
                log_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            messagebox.showinfo("Log Viewer", "No game log found. Play a game to create one.");
            return
        dialog = Toplevel(self);
        dialog.title("Last Game Log");
        dialog.geometry("500x600")
        log_text_widget = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, font=("Courier", 10))
        log_text_widget.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        formatted_log = ""
        for entry in log_data:
            formatted_log += f"--- Turn {entry['turn']} ({entry['player']}) ---\n";
            formatted_log += f"Move Played: {entry['move']}\n"
            if entry['player'] == 'AI':
                formatted_log += "\n  AI Analysis:\n";
                analysis = entry.get('analysis', {})
                formatted_log += f"  Total Simulations: {analysis.get('total_simulations', 'N/A')}\n"
                formatted_log += f"  {'Move':<6}{'Win%':<10}{'Visits':<8}\n";
                formatted_log += f"  {'------':<6}{'------':<10}{'------':<8}\n"
                for move_data in analysis.get('top_moves', []):
                    win_rate_str = f"{move_data.get('win_rate', 0):.2f}"
                    formatted_log += f"  {move_data.get('move', ''):<6}{win_rate_str:<10}{move_data.get('visits', ''):<8}\n"
            formatted_log += "\n" + "=" * 40 + "\n\n"
        log_text_widget.insert(tk.END, formatted_log);
        log_text_widget.config(state=tk.DISABLED)

    # --- Visualization Methods ---
    def _toggle_visualization(self):
        """Toggle visualization on/off."""
        self.viz_enabled = self.viz_enabled_var.get()
        if self.ai:
            self.ai.visualization_enabled = self.viz_enabled
        if self.viz_enabled:
            self._append_viz_text("=== Visualization Enabled ===\n", "phase")
        else:
            self._append_viz_text("=== Visualization Disabled ===\n", "info")
            self._clear_ghost_pieces()

    def _update_viz_rate(self):
        """Update the visualization update rate."""
        try:
            self.viz_update_rate = int(self.viz_rate_var.get())
        except ValueError:
            self.viz_update_rate = 10

    def _clear_viz_log(self):
        """Clear the visualization text log."""
        self.viz_text.delete(1.0, tk.END)

    def _append_viz_text(self, text, tag=None):
        """Append text to the visualization log."""
        self.viz_text.insert(tk.END, text, tag)
        self.viz_text.see(tk.END)

    def _viz_callback(self, event_type, data):
        """Callback for visualization events from MCTS."""
        if not self.viz_enabled:
            return

        # Filter events BEFORE queueing to avoid queue buildup
        iteration = data.get('iteration', 0)
        if event_type in ['selection', 'expansion', 'simulation', 'backpropagation', 'iteration_start']:
            if iteration % self.viz_update_rate != 0:
                return

        # Limit queue size to prevent memory issues
        if self.viz_queue.qsize() < 1000:
            self.viz_queue.put((event_type, data))

    def _process_viz_queue(self):
        """Process visualization events from the queue."""
        try:
            # Process up to 10 events per cycle to avoid overwhelming the UI
            for _ in range(10):
                if not self.viz_queue.empty():
                    event_type, data = self.viz_queue.get_nowait()
                    self._handle_viz_event(event_type, data)
                else:
                    break
        except queue.Empty:
            pass
        finally:
            # Schedule next processing - faster cycle for real-time updates
            self.after(16, self._process_viz_queue)  # ~60fps

    def _handle_viz_event(self, event_type, data):
        """Handle a visualization event."""
        if event_type == 'search_start':
            self._append_viz_text(f"\n{'='*40}\n", "phase")
            self._append_viz_text(f"SEARCH START\n", "phase")
            self._append_viz_text(f"Time limit: {data['time_limit_ms']}ms, Min sims: {data['min_simulations']}\n", "info")
            self._append_viz_text(f"{'='*40}\n\n", "phase")

        elif event_type == 'immediate_move':
            self._append_viz_text(f"IMMEDIATE MOVE DETECTED\n", "phase")
            self._append_viz_text(f"Move: {data['move']}, Reason: {data['reason']}, Score: {data['score']}\n\n", "info")

        elif event_type == 'iteration_start':
            if data['iteration'] % self.viz_update_rate == 0:
                self._append_viz_text(f"--- Iteration {data['iteration']} ---\n", "info")

        elif event_type == 'selection':
            self._append_viz_text(f"  SELECTION: ", "phase")
            path_str = " -> ".join(str(m) for m in data['path'][:3])
            if len(data['path']) > 3:
                path_str += f" ... ({len(data['path'])} moves)"
            self._append_viz_text(f"{path_str}\n", "selection")
            self._draw_ghost_path(data['path'], 'selection')

        elif event_type == 'expansion':
            self._append_viz_text(f"  EXPANSION: ", "phase")
            top_candidates = data['candidates'][:3]
            cand_str = ", ".join(f"{m}({s})" for s, m in top_candidates)
            self._append_viz_text(f"{cand_str}\n", "expansion")
            self._draw_ghost_candidates([m for _, m in top_candidates], 'expansion')

        elif event_type == 'simulation':
            self._append_viz_text(f"  SIMULATION: ", "phase")
            self._append_viz_text(f"{len(data['moves'])} moves, winner: {data['winner']}\n", "simulation")
            if data['moves']:
                self._draw_ghost_path(data['moves'], 'simulation')

        elif event_type == 'backpropagation':
            self._append_viz_text(f"  BACKPROP: ", "phase")
            path_str = " <- ".join(str(m) for m in data['path'][:3])
            if len(data['path']) > 3:
                path_str += f" ... ({len(data['path'])} nodes)"
            self._append_viz_text(f"{path_str}, winner: {data['winner']}\n\n", "backprop")

        elif event_type == 'search_complete':
            self._append_viz_text(f"\n{'='*40}\n", "phase")
            self._append_viz_text(f"SEARCH COMPLETE\n", "phase")
            self._append_viz_text(f"Total iterations: {data['total_iterations']}, Time: {data['time_elapsed']:.1f}ms\n", "info")
            self._append_viz_text(f"{'='*40}\n\n", "phase")
            self._clear_ghost_pieces()

    def _clear_ghost_pieces(self):
        """Clear all ghost pieces from the board."""
        for item in self.ghost_pieces:
            self.canvas.delete(item)
        self.ghost_pieces = []

    def _draw_ghost_path(self, moves, phase):
        """Draw ghost pieces for a path of moves."""
        if not self.game:
            return
        self._clear_ghost_pieces()

        colors = {
            'selection': '#90EE90',  # Light green
            'simulation': '#DDA0DD',  # Plum
            'expansion': '#FFB366'    # Light orange
        }
        color = colors.get(phase, '#CCCCCC')

        for i, move in enumerate(moves[:5]):  # Only show first 5
            if move is None:
                continue
            row, col = divmod(move, BOARD_SIZE)
            x0 = PADDING + col * CELL_SIZE - CELL_SIZE // 3
            y0 = PADDING + row * CELL_SIZE - CELL_SIZE // 3
            x1 = PADDING + col * CELL_SIZE + CELL_SIZE // 3
            y1 = PADDING + row * CELL_SIZE + CELL_SIZE // 3

            # Fade opacity for later moves
            opacity = 255 - (i * 40)
            if opacity < 100:
                opacity = 100

            item = self.canvas.create_oval(x0, y0, x1, y1,
                                           fill=color,
                                           outline='gray',
                                           stipple='gray50',
                                           tags='ghost')
            self.ghost_pieces.append(item)

    def _draw_ghost_candidates(self, moves, phase):
        """Draw ghost pieces for candidate moves."""
        self._draw_ghost_path(moves, phase)

if __name__ == "__main__":
    app = GomokuGUI()
    app.mainloop()