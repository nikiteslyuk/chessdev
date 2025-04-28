import tkinter as tk
from tkinter import Canvas, messagebox
from PIL import Image, ImageTk
import math
import os
import copy

CELL_SIZE = 80
BOARD_SIZE = 8
DARK_COLOR = "#7D945D"
LIGHT_COLOR = "#EEEED2"
HIGHLIGHT_COLOR = "#F6F669"
CAPTURE_COLOR = "#FF6961"
CHECK_COLOR = "#FF0000"

PIECE_MAP = {
    "P": "wp.png",
    "R": "wr.png",
    "N": "wkn.png",
    "B": "wb.png",
    "Q": "wq.png",
    "K": "wk.png",
    "p": "bp.png",
    "r": "br.png",
    "n": "bkn.png",
    "b": "bb.png",
    "q": "bq.png",
    "k": "bk.png",
}


class ChessGUI:
    def __init__(self, root, start_side="white", timer_seconds=15, increment=0):
        self.root = root
        self.canvas = Canvas(
            root, width=CELL_SIZE * BOARD_SIZE, height=CELL_SIZE * BOARD_SIZE
        )
        self.canvas.pack()
        self.board = self.init_board()
        self.selected_piece = None
        self.valid_moves = []
        self.dragging_piece = None
        self.start_cell = None
        self.current_pos = None
        self.images = {}
        self.turn = start_side
        self.check_pos = None
        self.increment = increment  # ДОБАВЛЕН ПАРАМЕТР ИНКРЕМЕНТА
        self.load_images()
        self.promotion_mode = False
        self.promotion_choices = []
        self.promotion_pos = None
        self.halfmove_clock = 0

        # Таймеры
        self.base_time = timer_seconds
        self.white_time = self.base_time
        self.black_time = self.base_time
        self.timer_label = tk.Label(root, font=("Arial", 16))
        self.timer_label.pack()
        self.active = True
        self.update_timer()

        # Для взятия на проходе
        self.en_passant_target = None
        self.en_passant_pos = None

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.draw_board()

    def update_timer(self):
        if not self.active:
            return
        if self.turn == "white":
            self.white_time -= 1
        else:
            self.black_time -= 1

        white_minutes, white_seconds = divmod(self.white_time, 60)
        black_minutes, black_seconds = divmod(self.black_time, 60)
        self.timer_label.config(
            text=f"White: {white_minutes:02d}:{white_seconds:02d}   Black: {black_minutes:02d}:{black_seconds:02d}"
        )

        if self.white_time <= 0:
            self.white_time = 0
            self.timer_label.config(
                text=f"White: 00:00   Black: {self.black_time // 60:02d}:{self.black_time % 60:02d}"
            )
            self.active = False
            self.draw_board()
            self.root.update_idletasks()  # ОБНОВЛЯЕМ ИНТЕРФЕЙС ДО ПОКАЗА ОКНА
            messagebox.showinfo("Время вышло", "Белые проиграли по времени")
            return
        elif self.black_time <= 0:
            self.black_time = 0
            self.timer_label.config(
                text=f"White: {self.white_time // 60:02d}:{self.white_time % 60:02d}   Black: 00:00"
            )
            self.active = False
            self.draw_board()
            self.root.update_idletasks()  # ОБНОВЛЯЕМ ИНТЕРФЕЙС ДО ПОКАЗА ОКНА
            messagebox.showinfo("Время вышло", "Черные проиграли по времени")
            return

        self.root.after(1000, self.update_timer)

    def load_images(self):
        for piece, filename in PIECE_MAP.items():
            path = os.path.join("figures", filename)
            img = Image.open(path).convert("RGBA").resize((CELL_SIZE, CELL_SIZE))
            self.images[piece] = ImageTk.PhotoImage(img)

    def init_board(self):
        board = [[None] * 8 for _ in range(8)]
        board[0] = ["r", "n", "b", "q", "k", "b", "n", "r"]
        board[1] = ["p"] * 8
        board[6] = ["P"] * 8
        board[7] = ["R", "N", "B", "Q", "K", "B", "N", "R"]
        return board

    def draw_board(self):
        self.canvas.delete("all")
        for y in range(BOARD_SIZE):
            for x in range(8):
                color = DARK_COLOR if (x + y) % 2 else LIGHT_COLOR
                if self.check_pos == (x, y):
                    color = CHECK_COLOR
                self.canvas.create_rectangle(
                    x * CELL_SIZE,
                    y * CELL_SIZE,
                    (x + 1) * CELL_SIZE,
                    (y + 1) * CELL_SIZE,
                    fill=color,
                    outline="",
                )
                if (x, y) in self.valid_moves:
                    if self.en_passant_target == (x, y):
                        fill_color = CAPTURE_COLOR
                    else:
                        target_piece = self.board[y][x]
                        fill_color = CAPTURE_COLOR if target_piece else HIGHLIGHT_COLOR
                    self.canvas.create_rectangle(
                        x * CELL_SIZE,
                        y * CELL_SIZE,
                        (x + 1) * CELL_SIZE,
                        (y + 1) * CELL_SIZE,
                        fill=fill_color,
                        stipple="gray50",
                    )

        for y in range(8):
            for x in range(8):
                piece = self.board[y][x]
                if piece and (
                    piece != self.dragging_piece or (x, y) != self.start_cell
                ):
                    self.draw_piece(piece, x, y)

        if self.dragging_piece and self.current_pos:
            x, y = self.current_pos
            self.canvas.create_image(x, y, image=self.images[self.dragging_piece])

        # Отрисовка меню выбора фигуры для превращения
        if self.promotion_mode:
            for (px, py), piece in self.promotion_choices:
                self.canvas.create_rectangle(
                    px * CELL_SIZE,
                    py * CELL_SIZE,
                    (px + 1) * CELL_SIZE,
                    (py + 1) * CELL_SIZE,
                    fill="#88C0D0",
                    outline="black",
                )
                self.draw_piece(piece, px, py)

    def draw_piece(self, piece, x, y):
        if piece in self.images:
            self.canvas.create_image(
                (x + 0.5) * CELL_SIZE, (y + 0.5) * CELL_SIZE, image=self.images[piece]
            )

    def pixel_to_cell(self, x, y):
        return x // CELL_SIZE, y // CELL_SIZE

    def get_possible_moves(self, piece, pos, board_state=None):
        board_state = board_state or self.board
        moves = []
        x, y = pos
        directions = []
        is_white = piece.isupper()

        def add_if_valid(nx, ny):
            if 0 <= nx < 8 and 0 <= ny < 8:
                target = board_state[ny][nx]
                if not target or (target.islower() if is_white else target.isupper()):
                    moves.append((nx, ny))

        if piece.lower() == "p":
            dir_y = -1 if is_white else 1
            start_row = 6 if is_white else 1
            if 0 <= y + dir_y < 8 and not board_state[y + dir_y][x]:
                moves.append((x, y + dir_y))
                if y == start_row and not board_state[y + 2 * dir_y][x]:
                    moves.append((x, y + 2 * dir_y))
            for dx in [-1, 1]:
                nx, ny = x + dx, y + dir_y
                if 0 <= nx < 8 and 0 <= ny < 8:
                    target = board_state[ny][nx]
                    if target and (target.islower() if is_white else target.isupper()):
                        moves.append((nx, ny))
                # Взятие на проходе
                if self.en_passant_target == (nx, ny):
                    moves.append((nx, ny))
        elif piece.lower() == "r":
            directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        elif piece.lower() == "b":
            directions = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
        elif piece.lower() == "q":
            directions = [
                (1, 0),
                (-1, 0),
                (0, 1),
                (0, -1),
                (1, 1),
                (-1, 1),
                (1, -1),
                (-1, -1),
            ]
        elif piece.lower() == "n":
            for dx, dy in [
                (-2, -1),
                (-2, 1),
                (2, -1),
                (2, 1),
                (-1, -2),
                (1, -2),
                (-1, 2),
                (1, 2),
            ]:
                add_if_valid(x + dx, y + dy)
        elif piece.lower() == "k":
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx or dy:
                        add_if_valid(x + dx, y + dy)

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            while 0 <= nx < 8 and 0 <= ny < 8:
                target = board_state[ny][nx]
                if not target:
                    moves.append((nx, ny))
                else:
                    if target.islower() if is_white else target.isupper():
                        moves.append((nx, ny))
                    break
                nx += dx
                ny += dy
        return moves

    def is_in_check(self, board_state, color):
        king = "K" if color == "white" else "k"
        king_pos = None
        for y in range(8):
            for x in range(8):
                if board_state[y][x] == king:
                    king_pos = (x, y)
                    break
        if not king_pos:
            return False
        for y in range(8):
            for x in range(8):
                piece = board_state[y][x]
                if piece and (
                    (piece.islower() and color == "white")
                    or (piece.isupper() and color == "black")
                ):
                    if king_pos in self.get_possible_moves(piece, (x, y), board_state):
                        return king_pos
        return False

    def is_checkmate_or_stalemate(self):
        for y in range(8):
            for x in range(8):
                piece = self.board[y][x]
                if piece and (
                    (self.turn == "white" and piece.isupper())
                    or (self.turn == "black" and piece.islower())
                ):
                    moves = self.get_possible_moves(piece, (x, y))
                    for move in moves:
                        new_board = copy.deepcopy(self.board)
                        new_board[move[1]][move[0]] = piece
                        new_board[y][x] = None
                        if not self.is_in_check(new_board, self.turn):
                            return None
        if self.is_in_check(self.board, self.turn):
            return "Checkmate"
        else:
            return "Stalemate"

    def filter_legal_moves(self, piece, pos):
        legal_moves = []
        moves = self.get_possible_moves(piece, pos)
        for move in moves:
            new_board = copy.deepcopy(self.board)
            new_board[move[1]][move[0]] = piece
            new_board[pos[1]][pos[0]] = None
            if not self.is_in_check(new_board, self.turn):
                legal_moves.append(move)
        return legal_moves

    def on_click(self, event):
        x, y = self.pixel_to_cell(event.x, event.y)

        # Обработка выбора фигуры для превращения
        if self.promotion_mode:
            for (px, py), piece in self.promotion_choices:
                if (x, y) == (px, py):
                    bx, by = self.promotion_pos
                    self.board[by][bx] = piece
                    self.promotion_mode = False
                    self.promotion_choices = []
                    self.turn = "black" if self.turn == "white" else "white"
                    self.check_pos = self.is_in_check(self.board, self.turn)

                    # Сброс таймера после превращения
                    if self.turn == "white":
                        self.white_time = self.base_time
                    else:
                        self.black_time = self.base_time

                    self.draw_board()

                    # Проверка на мат/пат после превращения
                    result = self.is_checkmate_or_stalemate()
                    if result == "Checkmate":
                        self.root.after(
                            500,
                            lambda: messagebox.showinfo(
                                "Игра окончена",
                                f"Мат. {self.turn.capitalize()} проиграли",
                            ),
                        )
                    elif result == "Stalemate":
                        self.root.after(
                            500,
                            lambda: messagebox.showinfo("Игра окончена", "Пат. Ничья"),
                        )
                    return

        # Обычный выбор фигуры
        if 0 <= x < 8 and 0 <= y < 8:
            piece = self.board[y][x]
            if piece and (
                (self.turn == "white" and piece.isupper())
                or (self.turn == "black" and piece.islower())
            ):
                self.selected_piece = piece
                self.start_cell = (x, y)
                self.valid_moves = self.filter_legal_moves(piece, (x, y))
            else:
                self.selected_piece = None
                self.valid_moves = []
        self.draw_board()

    def on_drag(self, event):
        if self.selected_piece:
            self.current_pos = (event.x, event.y)
            self.dragging_piece = self.selected_piece
            self.draw_board()

    def on_release(self, event):
        if self.selected_piece and self.start_cell:
            x, y = self.pixel_to_cell(event.x, event.y)
            target = (x, y)
            sx, sy = self.start_cell
            if target in self.valid_moves:
                is_en_passant = (
                    self.selected_piece.lower() == "p"
                    and target == self.en_passant_target
                )
                self.animate_back_to_cell(
                    target[0],
                    target[1],
                    valid=True,
                    sx=sx,
                    sy=sy,
                    tx_final=target[0],
                    ty_final=target[1],
                    is_en_passant=is_en_passant,
                )
            else:
                self.animate_back_to_cell(sx, sy, valid=False)

    def show_promotion_choices(self):
        x, y = self.promotion_pos
        # Чётко проверяем цвет пешки и даём белые или чёрные фигуры
        pieces = (
            ["Q", "R", "B", "N"]
            if self.selected_piece.isupper()
            else ["q", "r", "b", "n"]
        )
        py = y
        self.promotion_choices = []
        for i, piece in enumerate(pieces):
            px = x
            py = y - i if y == 7 else y + i
            if 0 <= py < 8:
                self.promotion_choices.append(((px, py), piece))
        self.draw_board()

    def animate_back_to_cell(
        self,
        tx,
        ty,
        valid,
        sx=None,
        sy=None,
        tx_final=None,
        ty_final=None,
        is_en_passant=False,
    ):
        if not self.dragging_piece or not self.current_pos:
            self.reset_selection()
            return

        cur_x, cur_y = self.current_pos
        target_x = (tx + 0.5) * CELL_SIZE
        target_y = (ty + 0.5) * CELL_SIZE
        dx = target_x - cur_x
        dy = target_y - cur_y
        dist = math.hypot(dx, dy)

        if dist < 5:
            if valid:
                self.board[sy][sx] = None
                captured = False

                if is_en_passant:
                    ep_x, ep_y = tx_final, sy
                    self.board[ep_y][ep_x] = None
                    captured = True
                elif self.board[ty_final][tx_final]:
                    captured = True

                self.board[ty_final][tx_final] = self.selected_piece

                # Инкремент времени
                if self.turn == "white":
                    self.white_time += self.increment
                else:
                    self.black_time += self.increment

                # Правило 50 ходов - сбрасываем, если взятие или ход пешкой
                if captured or self.selected_piece.lower() == "p":
                    self.halfmove_clock = 0
                else:
                    self.halfmove_clock += 1

                # Проверка на превращение пешки
                if self.selected_piece.lower() == "p" and (
                    ty_final == 0 or ty_final == 7
                ):
                    self.promotion_mode = True
                    self.promotion_pos = (tx_final, ty_final)
                    self.show_promotion_choices()
                    self.reset_selection()
                    return

                # Взятие на проходе доступно?
                if self.selected_piece.lower() == "p" and abs(ty_final - sy) == 2:
                    self.en_passant_target = (sx, (sy + ty_final) // 2)
                    self.en_passant_pos = (tx_final, ty_final)
                else:
                    self.en_passant_target = None
                    self.en_passant_pos = None

                self.turn = "black" if self.turn == "white" else "white"
                self.check_pos = self.is_in_check(self.board, self.turn)

                # Сброс таймера на следующий ход
                if self.turn == "white":
                    self.white_time = self.base_time
                else:
                    self.black_time = self.base_time

                self.draw_board()

                # Проверка мата/пата
                result = self.is_checkmate_or_stalemate()
                if result == "Checkmate":
                    self.check_pos = self.is_in_check(self.board, self.turn)
                    self.reset_selection()
                    self.draw_board()
                    self.active = False
                    self.root.after(
                        500,
                        lambda: messagebox.showinfo(
                            "Игра окончена", f"Мат. {self.turn.capitalize()} проиграли"
                        ),
                    )
                    return
                elif result == "Stalemate":
                    self.reset_selection()
                    self.draw_board()
                    self.active = False
                    self.root.after(
                        500, lambda: messagebox.showinfo("Игра окончена", "Пат. Ничья")
                    )
                    return

                # Проверка правила 50 ходов
                if self.halfmove_clock >= 50:
                    self.reset_selection()
                    self.draw_board()
                    self.active = False
                    self.root.after(
                        500,
                        lambda: messagebox.showinfo(
                            "Игра окончена", "Ничья по правилу 50 ходов"
                        ),
                    )
                    return

            self.reset_selection()
            return
        else:
            step_x = dx * 0.2
            step_y = dy * 0.2
            self.current_pos = (cur_x + step_x, cur_y + step_y)
            self.draw_board()
            self.canvas.after(
                16,
                lambda: self.animate_back_to_cell(
                    tx, ty, valid, sx, sy, tx_final, ty_final, is_en_passant
                ),
            )

    def reset_selection(self):
        self.selected_piece = None
        self.valid_moves = []
        self.dragging_piece = None
        self.current_pos = None
        self.start_cell = None
        self.draw_board()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Полноценные шахматы с таймером и взятием на проходе")
    game = ChessGUI(root, start_side="white", timer_seconds=1500, increment=1)
    root.mainloop()
