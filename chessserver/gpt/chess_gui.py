import tkinter as tk
from tkinter import Toplevel, messagebox
from PIL import Image, ImageTk


class ChessGUI(tk.Frame):
    def __init__(self, parent, logic, user_color="white", server_move_callback=None):
        super().__init__(parent)
        self.logic = logic
        self.user_color = user_color  # 'white' or 'black'
        self.server_move_callback = server_move_callback
        self.square_size = 64  # pixel size of each square
        # Colors for board squares
        self.light_color = "#F0D9B5"
        self.dark_color = "#B58863"
        # Flags for state
        self.dragging_piece = None  # canvas item id of piece being dragged
        self.drag_start_pos = None  # (row,col) of piece's original position
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.animating = False
        self.game_over = False

        # Create canvas for drawing the board
        canvas_width = canvas_height = 8 * self.square_size
        self.canvas = tk.Canvas(self, width=canvas_width, height=canvas_height)
        self.canvas.pack()
        # Load piece images
        self.images = {
            "P": ImageTk.PhotoImage(file="figures/wp.png"),
            "R": ImageTk.PhotoImage(file="figures/wr.png"),
            "N": ImageTk.PhotoImage(file="figures/wkn.png"),
            "B": ImageTk.PhotoImage(file="figures/wb.png"),
            "Q": ImageTk.PhotoImage(file="figures/wq.png"),
            "K": ImageTk.PhotoImage(file="figures/wk.png"),
            "p": ImageTk.PhotoImage(file="figures/bp.png"),
            "r": ImageTk.PhotoImage(file="figures/br.png"),
            "n": ImageTk.PhotoImage(file="figures/bkn.png"),
            "b": ImageTk.PhotoImage(file="figures/bb.png"),
            "q": ImageTk.PhotoImage(file="figures/bq.png"),
            "k": ImageTk.PhotoImage(file="figures/bk.png"),
        }

        # Draw board and initial pieces
        self.draw_board()
        self.draw_pieces()

        # Bind mouse events for dragging pieces
        self.canvas.bind("<Button-1>", self.on_piece_press)
        self.canvas.bind("<B1-Motion>", self.on_piece_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_piece_release)

    def draw_board(self):
        """Draw the chess board squares."""
        self.canvas.delete("square")
        for i in range(8):
            for j in range(8):
                # Determine logic coordinates for this square depending on orientation
                if self.user_color == "white":
                    logic_r, logic_c = i, j
                else:
                    logic_r, logic_c = 7 - i, 7 - j
                color = (
                    self.light_color
                    if (logic_r + logic_c) % 2 == 0
                    else self.dark_color
                )
                x0 = j * self.square_size
                y0 = i * self.square_size
                x1 = x0 + self.square_size
                y1 = y0 + self.square_size
                self.canvas.create_rectangle(
                    x0, y0, x1, y1, fill=color, outline=color, tags="square"
                )

    def draw_pieces(self):
        """Draw all pieces on the board according to the logic's board state."""
        # Initialize mappings from board positions to canvas items
        self.pos_to_id = {}
        self.id_to_pos = {}
        # Draw each piece from logic.board
        for r in range(8):
            for c in range(8):
                piece = self.logic.board[r][c]
                if piece:
                    x, y = self.logic_to_canvas(r, c)
                    image = self.images.get(piece)
                    item_id = self.canvas.create_image(x, y, image=image)
                    self.canvas.tag_raise(item_id)  # raise pieces above squares
                    self.canvas.addtag_withtag("piece", item_id)
                    self.pos_to_id[(r, c)] = item_id
                    self.id_to_pos[item_id] = (r, c)

    def logic_to_canvas(self, row, col):
        """Convert logic board coordinates (row,col) to canvas pixel coordinates (center of square)."""
        if self.user_color == "white":
            screen_row = row
            screen_col = col
        else:
            # Flip for black orientation
            screen_row = 7 - row
            screen_col = 7 - col
        x = screen_col * self.square_size + self.square_size // 2
        y = screen_row * self.square_size + self.square_size // 2
        return x, y

    def canvas_to_logic(self, x, y):
        """Convert canvas pixel coordinates to logic board coordinates (row,col)."""
        screen_col = int((x) // self.square_size)
        screen_row = int((y) // self.square_size)
        # Use rounding for magnetic snap threshold (closest square)
        if (x % self.square_size) > (self.square_size / 2):
            screen_col = min(screen_col + 1, 7)
        if (y % self.square_size) > (self.square_size / 2):
            screen_row = min(screen_row + 1, 7)
        if self.user_color == "white":
            logic_row = screen_row
            logic_col = screen_col
        else:
            logic_row = 7 - screen_row
            logic_col = 7 - screen_col
        return logic_row, logic_col

    def on_piece_press(self, event):
        """Mouse press event on canvas - select a piece to drag if it's the player's turn."""
        if self.game_over or self.animating:
            return
        # Determine which square was clicked
        logic_r, logic_c = self.canvas_to_logic(event.x, event.y)
        # Check if a piece exists there and if it's the player's piece and their turn
        piece = self.logic.board[logic_r][logic_c]
        if not piece:
            return  # empty square
        # Only allow dragging the player's own pieces and only on their turn
        player_is_white = self.user_color == "white"
        if player_is_white and not piece.isupper():
            return
        if not player_is_white and not piece.islower():
            return
        if self.logic.turn != self.user_color:
            return  # not this side's turn to move
        # This is a valid piece to move. Start dragging.
        item_id = self.pos_to_id.get((logic_r, logic_c))
        if not item_id:
            return
        self.dragging_piece = item_id
        self.drag_start_pos = (logic_r, logic_c)
        # Calculate offset of cursor within the piece image for smooth dragging
        curr_x, curr_y = self.canvas.coords(item_id)
        self.drag_offset_x = curr_x - event.x
        self.drag_offset_y = curr_y - event.y
        # Raise the piece above others while dragging
        self.canvas.tag_raise(item_id)
        # Show possible moves for this piece
        moves = self.logic.generate_moves(self.logic.turn)
        self.highlight_moves = []
        for move in moves:
            if move["from"] == (logic_r, logic_c):
                tr, tc = move["to"]
                # Determine display coordinates for target
                tx, ty = self.logic_to_canvas(tr, tc)
                if self.logic.board[tr][tc] is None and not move.get("en_passant"):
                    # Empty square move: draw a small circle
                    radius = 10
                    highlight = self.canvas.create_oval(
                        tx - radius,
                        ty - radius,
                        tx + radius,
                        ty + radius,
                        fill="orange",
                        outline="",
                    )
                else:
                    # Capture move (or en passant target): draw a red outline circle
                    radius = self.square_size // 2 - 4
                    highlight = self.canvas.create_oval(
                        tx - radius,
                        ty - radius,
                        tx + radius,
                        ty + radius,
                        outline="red",
                        width=3,
                    )
                self.canvas.addtag_withtag("highlight", highlight)
                self.highlight_moves.append(highlight)

    def on_piece_drag(self, event):
        """Mouse drag (motion) event - move the currently selected piece with the cursor."""
        if not self.dragging_piece:
            return
        # Move the piece's canvas image to follow the cursor (with offset)
        x = event.x + self.drag_offset_x
        y = event.y + self.drag_offset_y
        self.canvas.coords(self.dragging_piece, x, y)

    def on_piece_release(self, event):
        """Mouse release event - drop the piece and finalize move if legal, or snap back if not."""
        if not self.dragging_piece:
            return
        # Remove highlight markers
        self.canvas.delete("highlight")
        # Determine target square nearest to drop point
        logic_target_r, logic_target_c = self.canvas_to_logic(event.x, event.y)
        from_r, from_c = self.drag_start_pos
        item_id = self.dragging_piece
        self.dragging_piece = None
        # If dropped back on original square (no move) or invalid destination, snap piece back
        if (logic_target_r, logic_target_c) == (from_r, from_c):
            # Snap back to original position
            x, y = self.logic_to_canvas(from_r, from_c)
            self.canvas.coords(item_id, x, y)
            return
        # Check if the move is legal
        legal = False
        promotion_choice = None
        moves = self.logic.generate_moves(self.logic.turn)
        for move in moves:
            if move["from"] == (from_r, from_c) and move["to"] == (
                logic_target_r,
                logic_target_c,
            ):
                # Found a matching move
                promotion_choice = move.get("promotion")
                # If promotion_choice is not None and not 'None', it means this move is a pawn reaching last rank.
                legal = True
                break
        if not legal:
            # Move is not legal: snap back to original square
            x, y = self.logic_to_canvas(from_r, from_c)
            self.canvas.coords(item_id, x, y)
            return
        # If the move is a pawn promotion, and multiple choices are possible, ask the user for promotion piece.
        chosen_promo = None
        if promotion_choice is not None:
            # promotion_choice from moves list will be one of 'Q','R','B','N' or default (if logic gave only one)
            # If logic offers multiple promotions, we'll open selection.
            choices = (
                ["Q", "R", "B", "N"]
                if self.logic.board[from_r][from_c].upper() == "P"
                and (logic_target_r in (0, 7))
                else []
            )
            if choices:
                # Create a modal dialog for promotion choice
                promo_win = Toplevel(self)
                promo_win.title("Promote pawn")
                promo_win.grab_set()  # make modal
                tk.Label(promo_win, text="Choose piece for promotion:").pack(pady=5)

                # Use piece images for choices
                def select_promo(piece):
                    nonlocal chosen_promo
                    chosen_promo = piece
                    promo_win.destroy()

                for p in choices:
                    img = self.images[p if self.user_color == "white" else p.lower()]
                    btn = tk.Button(
                        promo_win, image=img, command=lambda p=p: select_promo(p)
                    )
                    btn.pack(side=tk.LEFT, padx=5, pady=5)
                promo_win.wait_window()
            # If user closed without selecting, default to Queen
            if not chosen_promo:
                chosen_promo = "Q"
        # Remove any captured piece's image (for normal captures or en passant)
        captured_piece_id = None
        # Normal capture
        if self.logic.board[logic_target_r][logic_target_c] is not None:
            captured_piece_id = self.pos_to_id.get((logic_target_r, logic_target_c))
        # En passant capture (target square is empty but pawn behind is captured)
        moving_piece = self.logic.board[from_r][from_c]
        if moving_piece and moving_piece.upper() == "P":
            if (logic_target_r, logic_target_c) == self.logic.en_passant_target:
                # Determine captured pawn's position
                if moving_piece.isupper():
                    # white pawn capturing downwards
                    capture_pos = (logic_target_r + 1, logic_target_c)
                else:
                    # black pawn capturing upwards
                    capture_pos = (logic_target_r - 1, logic_target_c)
                captured_piece_id = self.pos_to_id.get(capture_pos)
        if captured_piece_id:
            # Remove the captured piece from canvas and mappings
            self.canvas.delete(captured_piece_id)
            if captured_piece_id in self.id_to_pos:
                cap_pos = self.id_to_pos[captured_piece_id]
                if cap_pos in self.pos_to_id:
                    del self.pos_to_id[cap_pos]
                del self.id_to_pos[captured_piece_id]
        # Snap the moving piece to the center of target square
        new_x, new_y = self.logic_to_canvas(logic_target_r, logic_target_c)
        self.canvas.coords(item_id, new_x, new_y)
        # Update logic state with the move
        result = self.logic.make_move(
            from_r, from_c, logic_target_r, logic_target_c, promotion=chosen_promo
        )
        # Update mapping of moved piece
        if (from_r, from_c) in self.pos_to_id:
            del self.pos_to_id[(from_r, from_c)]
        self.pos_to_id[(logic_target_r, logic_target_c)] = item_id
        self.id_to_pos[item_id] = (logic_target_r, logic_target_c)
        # If promotion happened, update the piece image on canvas
        if result and result["promotion"]:
            new_piece = self.logic.board[logic_target_r][
                logic_target_c
            ]  # e.g. 'Q' or 'q'
            new_image = self.images.get(new_piece)
            if new_image:
                self.canvas.itemconfig(item_id, image=new_image)
        # Check for game end conditions (checkmate, stalemate, 50-move rule)
        self.check_game_status()
        if self.game_over:
            return
        # Opponent's turn: get move from "server"
        if self.server_move_callback:
            opp_move = self.server_move_callback(
                result
            )  # send user's move (though server stub might not use it)
            if opp_move:
                self.perform_opponent_move(opp_move)

    def perform_opponent_move(self, move):
        """Animate and apply the opponent's move (move is a dict with 'from' and 'to', and possibly 'promotion')."""
        self.animating = True
        from_r, from_c = move["from"]
        to_r, to_c = move["to"]
        promo = move.get("promotion")
        # Determine if there's a capture
        captured_id = None
        if move.get("en_passant"):
            # En passant capture: target square is empty, pawn behind is captured
            if self.logic.board[from_r][from_c].islower():
                # black pawn capturing white pawn upward
                capture_pos = (to_r - 1, to_c)
            else:
                # white pawn capturing black pawn downward
                capture_pos = (to_r + 1, to_c)
            captured_id = self.pos_to_id.get(capture_pos)
        else:
            # Normal capture
            captured_id = self.pos_to_id.get((to_r, to_c))
        # Remove captured piece from canvas immediately
        if captured_id:
            self.canvas.delete(captured_id)
            if captured_id in self.id_to_pos:
                cap_pos = self.id_to_pos[captured_id]
                if cap_pos in self.pos_to_id:
                    del self.pos_to_id[cap_pos]
                del self.id_to_pos[captured_id]
        # Identify the moving piece's canvas item
        moving_id = self.pos_to_id.get((from_r, from_c))
        if not moving_id:
            # This might happen if moving piece was just created by promotion last move (and mapping updated accordingly).
            # To handle that scenario properly, ensure mapping is correct. Otherwise, try to find item by logic if needed.
            for item, pos in self.id_to_pos.items():
                if pos == (from_r, from_c):
                    moving_id = item
                    break
        # Update logic state for opponent's move
        result = self.logic.make_move(from_r, from_c, to_r, to_c, promotion=promo)
        # Animate the moving piece from start to end
        if moving_id:
            start_x, start_y = self.logic_to_canvas(from_r, from_c)
            end_x, end_y = self.logic_to_canvas(to_r, to_c)
            steps = 10
            dx = (end_x - start_x) / steps
            dy = (end_y - start_y) / steps
            # Animation loop using after
            for i in range(steps):
                self.canvas.move(moving_id, dx, dy)
                self.canvas.update()
                self.canvas.after(20)
            # Ensure final position exact
            self.canvas.coords(moving_id, end_x, end_y)
        # If castling, also move the rook
        if result and result.get("castle"):
            king_from = (from_r, from_c)
            king_to = (to_r, to_c)
            # Determine rook move from king move
            if king_to[1] == 6:  # king-side
                rook_from = (from_r, 7)
                rook_to = (from_r, 5)
            else:  # queen-side
                rook_from = (from_r, 0)
                rook_to = (from_r, 3)
            rook_id = self.pos_to_id.get(rook_from)
            if rook_id:
                # Animate rook (we can do it quickly without many steps)
                rx0, ry0 = self.logic_to_canvas(*rook_from)
                rx1, ry1 = self.logic_to_canvas(*rook_to)
                self.canvas.coords(rook_id, rx1, ry1)
                # Update mapping for rook
                del self.pos_to_id[rook_from]
                self.pos_to_id[rook_to] = rook_id
                self.id_to_pos[rook_id] = rook_to
        # If promotion, update piece image
        if result and result["promotion"]:
            new_piece = self.logic.board[to_r][to_c]
            new_image = self.images.get(new_piece)
            if new_image and moving_id:
                self.canvas.itemconfig(moving_id, image=new_image)
        # Update position mapping for moving piece
        if moving_id:
            if (from_r, from_c) in self.pos_to_id:
                del self.pos_to_id[(from_r, from_c)]
            self.pos_to_id[(to_r, to_c)] = moving_id
            self.id_to_pos[moving_id] = (to_r, to_c)
        # Opponent move done
        self.animating = False
        # Check for game over conditions after opponent move
        self.check_game_status()

    def check_game_status(self):
        """Check for check, checkmate, stalemate, or 50-move draw and handle game over."""
        # Highlight king in check if any
        self.canvas.delete("check_highlight")
        if self.logic.is_in_check("white"):
            # Highlight white king square in red
            king_pos = None
            for pos, item in self.pos_to_id.items():
                if self.logic.board[pos[0]][pos[1]] == "K":
                    king_pos = pos
                    break
            if king_pos:
                x0 = (
                    0 if self.user_color == "white" else 7
                ) * self.square_size  # not directly, better compute as in draw_board
            # Actually, easier: find white king position and draw rectangle at that logic coordinate
            if king_pos:
                # Compute top-left of that square on canvas
                if self.user_color == "white":
                    screen_row = king_pos[0]
                    screen_col = king_pos[1]
                else:
                    screen_row = 7 - king_pos[0]
                    screen_col = 7 - king_pos[1]
                x0 = screen_col * self.square_size
                y0 = screen_row * self.square_size
                x1 = x0 + self.square_size
                y1 = y0 + self.square_size
                self.canvas.create_rectangle(
                    x0, y0, x1, y1, outline="red", width=3, tags="check_highlight"
                )
        if self.logic.is_in_check("black"):
            # Highlight black king square in red
            king_pos = None
            for pos, item in self.pos_to_id.items():
                if self.logic.board[pos[0]][pos[1]] == "k":
                    king_pos = pos
                    break
            if king_pos:
                if self.user_color == "white":
                    screen_row = king_pos[0]
                    screen_col = king_pos[1]
                else:
                    screen_row = 7 - king_pos[0]
                    screen_col = 7 - king_pos[1]
                x0 = screen_col * self.square_size
                y0 = screen_row * self.square_size
                x1 = x0 + self.square_size
                y1 = y0 + self.square_size
                self.canvas.create_rectangle(
                    x0, y0, x1, y1, outline="red", width=3, tags="check_highlight"
                )
        # Check for no legal moves (mate or stalemate)
        current_color = self.logic.turn
        moves = self.logic.generate_moves(current_color)
        if not moves:
            if self.logic.is_in_check(current_color):
                # Checkmate
                winner = "White" if current_color == "black" else "Black"
                messagebox.showinfo("Game Over", f"Checkmate! {winner} wins.")
            else:
                # Stalemate
                messagebox.showinfo("Game Over", "Stalemate! It's a draw.")
            self.game_over = True
        # 50-move rule
        if self.logic.halfmove_clock >= 100 and not self.game_over:
            messagebox.showinfo("Game Over", "Draw by 50-move rule.")
            self.game_over = True
