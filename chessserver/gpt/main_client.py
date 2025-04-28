import tkinter as tk
from chess_logic import ChessLogic
from chess_gui import ChessGUI
import random


# Server stub function to simulate opponent. It takes the user's move (not used in this simple stub)
# and returns a random legal move for the opponent using ChessLogic.
def server_make_move(user_move):
    # The ChessLogic instance is global or passed in; here we'll assume a global 'logic' defined below.
    global logic
    # Generate all legal moves for the side whose turn it is now
    moves = logic.generate_moves()
    if not moves:
        return None
    # Choose a random move
    move = random.choice(moves)
    return move


if __name__ == "__main__":
    logic = ChessLogic()
    root = tk.Tk()
    root.title("Chess Client")
    # You can set user_color to 'white' or 'black'
    user_color = "white"
    gui = ChessGUI(
        root, logic, user_color=user_color, server_move_callback=server_make_move
    )
    gui.pack()
    # If user plays black, let the server (white) make the first move
    if user_color == "black":
        first_move = server_make_move(None)
        if first_move:
            gui.perform_opponent_move(first_move)
    root.mainloop()
