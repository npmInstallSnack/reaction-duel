# Authors: Kahekili Spears, Jack O'Brien, Woody Churchward
# Date created: 10/20/26
# Date modified: 10/20/26
# Purpose: Reaction time game

import random
import time
import tkinter as tk

# ---------- Settings ----------
WIN_SCORE = 3            # first to 3 = best of 5
MIN_WAIT_MS = 1500       # shortest wait before GO
MAX_WAIT_MS = 5000       # longest wait before GO
P1_KEY = "a"
P2_KEY = "l"

# ---------- Colors ----------
COLOR_IDLE = "#2b2d42"
COLOR_WAIT = "#d90429"
COLOR_GO = "#2dc653"
COLOR_RESULT = "#3a86ff"
COLOR_TEXT = "#ffffff"

# ---------- Game states ----------
STATE_IDLE = "idle"              # waiting for SPACE to start a round
STATE_WAITING = "waiting"        # red screen, don't press yet!
STATE_GO = "go"                  # green screen, press NOW
STATE_ROUND_OVER = "round_over"  # showing who won the round
STATE_MATCH_OVER = "match_over"  # someone hit WIN_SCORE


class ReactionDuel:
    def __init__(self, root):
        self.root = root
        self.root.title("Reaction Duel")
        self.root.geometry("800x500")
        self.root.configure(bg=COLOR_IDLE)

        # Game data
        self.state = STATE_IDLE
        self.p1_score = 0
        self.p2_score = 0
        self.round_number = 0
        self.go_time = 0.0
        self.go_job = None  # id of the scheduled "turn green" callback

        self.build_ui()

        self.root.bind("<KeyPress>", self.on_key)
        self.show_idle()

    # ---------- UI ----------
    def build_ui(self):
        self.score_label = tk.Label(
            self.root, text="", font=("Helvetica", 28, "bold"),
            bg=COLOR_IDLE, fg=COLOR_TEXT,
        )
        self.score_label.pack(pady=(20, 0))

        self.round_label = tk.Label(
            self.root, text="", font=("Helvetica", 16),
            bg=COLOR_IDLE, fg=COLOR_TEXT,
        )
        self.round_label.pack()

        self.main_label = tk.Label(
            self.root, text="", font=("Helvetica", 48, "bold"),
            bg=COLOR_IDLE, fg=COLOR_TEXT, wraplength=700,
        )
        self.main_label.pack(expand=True)

        self.sub_label = tk.Label(
            self.root, text="", font=("Helvetica", 18),
            bg=COLOR_IDLE, fg=COLOR_TEXT, wraplength=700,
        )
        self.sub_label.pack(pady=(0, 40))

    def set_background(self, color):
        """Paint the window and every label the same color."""
        self.root.configure(bg=color)
        self.score_label.configure(bg=color)
        self.round_label.configure(bg=color)
        self.main_label.configure(bg=color)
        self.sub_label.configure(bg=color)

    def update_scoreboard(self):
        self.score_label.configure(
            text=f"P1 ({P1_KEY.upper()})  {self.p1_score}  -  {self.p2_score}  P2 ({P2_KEY.upper()})"
        )

    # ---------- Screens ----------
    def show_idle(self):
        self.state = STATE_IDLE
        self.set_background(COLOR_IDLE)
        self.update_scoreboard()
        self.round_label.configure(text=f"First to {WIN_SCORE} wins")
        self.main_label.configure(text="REACTION DUEL")
        self.sub_label.configure(text="Press SPACE to start the round")

    def show_waiting(self):
        self.state = STATE_WAITING
        self.set_background(COLOR_WAIT)
        self.round_label.configure(text=f"Round {self.round_number}")
        self.main_label.configure(text="WAIT...")
        self.sub_label.configure(text="Don't press yet!")

    def show_go(self):
        self.state = STATE_GO
        self.go_time = time.perf_counter()
        self.set_background(COLOR_GO)
        self.main_label.configure(text="GO!")
        self.sub_label.configure(text="")

    def show_round_result(self, headline, detail):
        self.state = STATE_ROUND_OVER
        self.set_background(COLOR_RESULT)
        self.update_scoreboard()
        self.main_label.configure(text=headline)
        self.sub_label.configure(text=detail + "\n\nPress SPACE for the next round")

    def show_match_result(self, headline, detail):
        self.state = STATE_MATCH_OVER
        self.set_background(COLOR_RESULT)
        self.update_scoreboard()
        self.main_label.configure(text=headline)
        self.sub_label.configure(text=detail + "\n\nPress SPACE for a new match")

    # ---------- Game flow ----------
    def start_round(self):
        self.round_number += 1
        self.show_waiting()
        delay = random.randint(MIN_WAIT_MS, MAX_WAIT_MS)
        self.go_job = self.root.after(delay, self.show_go)

    def start_new_match(self):
        self.p1_score = 0
        self.p2_score = 0
        self.round_number = 0
        self.show_idle()

    def player_name(self, player):
        return "Player 1" if player == 1 else "Player 2"

    def award_point(self, winner):
        if winner == 1:
            self.p1_score += 1
        else:
            self.p2_score += 1

    def end_round(self, winner, detail):
        """Give the winner a point, then show either round or match results."""
        self.award_point(winner)
        name = self.player_name(winner)

        if self.p1_score >= WIN_SCORE or self.p2_score >= WIN_SCORE:
            self.show_match_result(f"{name} WINS THE MATCH!", detail)
        else:
            self.show_round_result(f"{name} wins the round!", detail)

    # ---------- Input ----------
    def on_key(self, event):
        key = event.keysym.lower()

        if key == "escape":
            self.root.destroy()
            return

        if key == "space":
            if self.state == STATE_IDLE or self.state == STATE_ROUND_OVER:
                self.start_round()
            elif self.state == STATE_MATCH_OVER:
                self.start_new_match()
            return

        # Figure out which player (if any) pressed their key
        if key == P1_KEY:
            player = 1
        elif key == P2_KEY:
            player = 2
        else:
            return

        if self.state == STATE_WAITING:
            self.handle_false_start(player)
        elif self.state == STATE_GO:
            self.handle_valid_press(player)

    def handle_false_start(self, player):
        """Pressed during the red screen: the OTHER player wins the round."""
        if self.go_job is not None:
            self.root.after_cancel(self.go_job)
            self.go_job = None
        winner = 2 if player == 1 else 1
        self.end_round(winner, f"{self.player_name(player)} jumped the gun! False start!")

    def handle_valid_press(self, player):
        """First valid press after GO wins the round."""
        reaction_ms = int((time.perf_counter() - self.go_time) * 1000)
        self.end_round(player, f"{self.player_name(player)} reacted in {reaction_ms} ms")


def main():
    root = tk.Tk()
    ReactionDuel(root)
    root.mainloop()


if __name__ == "__main__":
    main()