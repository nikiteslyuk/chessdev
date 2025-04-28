import tkinter as tk
from tkinter import Canvas, messagebox
from PIL import Image, ImageTk
import math
import os
import copy


def print_board(board):
    print("   a b c d e f g h")
    print("  -----------------")
    for i, row in enumerate(board):
        line = f"{8 - i} |"
        for cell in row:
            line += f"{cell if cell else '.'} "
        print(line + f"| {8 - i}")
    print("  -----------------")
    print("   a b c d e f g h")


CELL_SIZE = 80
BOARD_SIZE = 8
DARK_COLOR = "#7D945D"
LIGHT_COLOR = "#EEEED2"

HIGHLIGHT_COLOR_MAP = {
    'move': "#F6F669",
    'capture': "#FF6961",
    'check': "#FF0000"
}

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

'''
общее
    1) очередность хода 
    2) ход оппонента получает от модели сервера
'''

# вся шахматная логика будет тут
'''
тут надо дописать еще 
    1) логику превращения 
    2) взятие на проходе 
    3) шахи
    4) маты/паты
    5) правило 50 ходов
    6) рокировки
'''


class ChessLogic:
    def __init__(self, myside: str = 'w', brd: list = None) -> None:
        self.myside = myside
        self.curr_move = 'w'
        self.board = []
        if brd:
            self.board = brd
            return
        self.board = [[''] * 8 for _ in range(8)]
        self.board[0] = ["r", "n", "b", "q", "k", "b", "n", "r"]
        self.board[1] = ["p"] * 8
        self.board[6] = ["P"] * 8
        self.board[7] = ["R", "N", "B", "Q", "K", "B", "N", "R"]

    def get_legal_moves(self, row: int, col: int) -> dict:
        if not (0 <= row < 8 and 0 <= col < 8):
            return {}
        piece = self.board[row][col]
        if not piece:
            return {}

        moves = {"move": [], "capture": []}
        is_white = piece.isupper()
        enemy = str.islower if is_white else str.isupper

        def add_move(r, c):
            if 0 <= r < 8 and 0 <= c < 8:
                target = self.board[r][c]
                if not target:
                    moves["move"].append((r, c))
                elif enemy(target):
                    moves["capture"].append((r, c))

        # Пешка
        if piece.lower() == "p":
            direction = -1 if is_white else 1
            # Ход вперед
            if 0 <= row + direction < 8 and not self.board[row + direction][col]:
                moves["move"].append((row + direction, col))
                # Двойной ход пешки с начальной позиции
                if (is_white and row == 6) or (not is_white and row == 1):
                    if not self.board[row + 2 * direction][col]:
                        moves["move"].append((row + 2 * direction, col))
            # Взятия по диагонали
            for dc in [-1, 1]:
                nr, nc = row + direction, col + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = self.board[nr][nc]
                    if target and enemy(target):
                        moves["capture"].append((nr, nc))

        # Конь
        elif piece.lower() == "n":
            knight_moves = [
                (row + 2, col + 1), (row + 2, col - 1),
                (row - 2, col + 1), (row - 2, col - 1),
                (row + 1, col + 2), (row + 1, col - 2),
                (row - 1, col + 2), (row - 1, col - 2),
            ]
            for r, c in knight_moves:
                add_move(r, c)

        # Ладья
        elif piece.lower() == "r":
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            for dr, dc in directions:
                r, c = row + dr, col + dc
                while 0 <= r < 8 and 0 <= c < 8:
                    target = self.board[r][c]
                    if not target:
                        moves["move"].append((r, c))
                    elif enemy(target):
                        moves["capture"].append((r, c))
                        break
                    else:
                        break
                    r += dr
                    c += dc

        # Слон
        elif piece.lower() == "b":
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dr, dc in directions:
                r, c = row + dr, col + dc
                while 0 <= r < 8 and 0 <= c < 8:
                    target = self.board[r][c]
                    if not target:
                        moves["move"].append((r, c))
                    elif enemy(target):
                        moves["capture"].append((r, c))
                        break
                    else:
                        break
                    r += dr
                    c += dc

        # Ферзь
        elif piece.lower() == "q":
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1),
                          (-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dr, dc in directions:
                r, c = row + dr, col + dc
                while 0 <= r < 8 and 0 <= c < 8:
                    target = self.board[r][c]
                    if not target:
                        moves["move"].append((r, c))
                    elif enemy(target):
                        moves["capture"].append((r, c))
                        break
                    else:
                        break
                    r += dr
                    c += dc

        # Король
        elif piece.lower() == "k":
            king_moves = [(-1, -1), (-1, 0), (-1, 1),
                          (0, -1), (0, 1),
                          (1, -1), (1, 0), (1, 1)]
            for dr, dc in king_moves:
                add_move(row + dr, col + dc)

        return moves


# вся отрисовка шахмат будет тут
'''
реализовать 
    1) поворот доски если играем черными (прописать перед каждым взятием координат функицю coord_reverse
'''


class ChessGUI(tk.Tk):
    def __init__(self, myside: str = 'w') -> None:
        super().__init__()
        self.title("Шахматы")
        self.geometry(f"{CELL_SIZE * BOARD_SIZE}x{CELL_SIZE * BOARD_SIZE}")
        self.resizable(False, False)
        self.canvas = Canvas(self, width=CELL_SIZE * BOARD_SIZE, height=CELL_SIZE * BOARD_SIZE)

        self.drag_data = {}

        self.logic = ChessLogic()

        self.images = {}
        self.load_images()

        self.highlighted_cells = []

        self.board_gui = []
        self.draw_board(True)

        self.ismoving = False
        self.moving_params = {
            "dragging_piece": None,
            "start_pos": None,
            "legal_moves": {},
            "drag_img_id": None,
            "current_x": 0,
            "current_y": 0
        }

        self.bind('<Motion>', self.possible_moves)
        self.canvas.bind("<Button-1>", self.take_piece)
        self.canvas.bind("<B1-Motion>", self.move_piece)
        self.canvas.bind("<ButtonRelease-1>", self.release_piece)

        self.canvas.pack()
        self.mainloop()

    def take_piece(self, event):
        col, row = event.x // CELL_SIZE, event.y // CELL_SIZE
        if not (0 <= row < 8 and 0 <= col < 8):
            return
        piece = self.logic.board[row][col]
        if piece:
            self.ismoving = True
            self.moving_params["dragging_piece"] = piece
            self.moving_params["start_pos"] = (row, col)
            self.moving_params["legal_moves"] = self.logic.get_legal_moves(row, col)

            # ВАЖНО: подсветку ставим ДО удаления фигуры
            self.clear_highlight()
            self.highlight_cells(self.moving_params["legal_moves"])

            # Убираем фигуру после подсветки
            self.logic.board[row][col] = ''
            self.draw_board()

            self.moving_params["drag_img_id"] = self.canvas.create_image(
                event.x, event.y, image=self.images[piece], tags="piece"
            )
            self.moving_params["current_x"] = event.x
            self.moving_params["current_y"] = event.y

    def move_piece(self, event):
        if self.logic.curr_move != self.logic.myside:
            return
        if self.moving_params["dragging_piece"]:
            self.moving_params["current_x"] = event.x
            self.moving_params["current_y"] = event.y
            self.canvas.coords(self.moving_params["drag_img_id"], event.x, event.y)

    def release_piece(self, event):
        if not self.moving_params["dragging_piece"] or not self.moving_params["start_pos"]:
            return

        col, row = event.x // CELL_SIZE, event.y // CELL_SIZE
        sx, sy = self.moving_params["start_pos"]

        # КОСТЫЛЬ — временно ставим фигуру обратно, чтобы получить правильные легальные ходы
        self.logic.board[sx][sy] = self.moving_params["dragging_piece"]
        self.moving_params["legal_moves"] = self.logic.get_legal_moves(sx, sy)
        self.logic.board[sx][sy] = ''  # снова убираем перед финальной проверкой

        valid_cells = self.moving_params["legal_moves"]["move"] + self.moving_params["legal_moves"]["capture"]

        if (row, col) in valid_cells:
            self.logic.board[row][col] = self.moving_params["dragging_piece"]
            self.logic.board[sx][sy] = ''
            self.magnet_piece_to_cell(row, col)
        else:
            self.logic.board[sx][sy] = self.moving_params["dragging_piece"]
            self.magnet_piece_to_cell(sx, sy)

    def magnet_piece_to_cell(self, target_row, target_col):
        cur_x, cur_y = self.moving_params["current_x"], self.moving_params["current_y"]
        target_x = target_col * CELL_SIZE + CELL_SIZE // 2
        target_y = target_row * CELL_SIZE + CELL_SIZE // 2
        dx = target_x - cur_x
        dy = target_y - cur_y
        dist = math.hypot(dx, dy)

        if dist < 5:
            self.moving_params["dragging_piece"] = None
            self.moving_params["start_pos"] = None
            self.ismoving = False
            self.clear_highlight()  # УБИРАЕМ подсветку после хода
            self.draw_board()
            return
        else:
            step_x = dx * 0.2
            step_y = dy * 0.2
            self.moving_params["current_x"] += step_x
            self.moving_params["current_y"] += step_y
            self.canvas.coords(self.moving_params["drag_img_id"], self.moving_params["current_x"],
                               self.moving_params["current_y"])
            self.canvas.after(16, lambda: self.magnet_piece_to_cell(target_row, target_col))

    def possible_moves(self, event) -> None:
        if self.ismoving:
            return  # Если тащу фигуру — не трогаем подсветку

        col = event.x // CELL_SIZE
        row = event.y // CELL_SIZE
        if 0 <= col < BOARD_SIZE and 0 <= row < BOARD_SIZE:
            if self.logic.board[row][col]:
                legalmoves = self.logic.get_legal_moves(row, col)
                self.highlight_cells(legalmoves)
                return

        # Если мышка не на фигуре — убираем подсветку
        self.clear_highlight()
        self.draw_board()

    def highlight_cells(self, legalmoves: dict[str, list[tuple[int, int]]]) -> None:
        self.clear_highlight()
        for key in legalmoves.keys():
            for coords in legalmoves[key]:
                row, col = coords
                self.canvas.itemconfig(self.board_gui[row][col], fill=HIGHLIGHT_COLOR_MAP[key])
                self.highlighted_cells.append((row, col))

    def clear_highlight(self) -> None:
        for row, col in self.highlighted_cells:
            color = DARK_COLOR if (row + col) % 2 else LIGHT_COLOR
            rect_id = self.board_gui[row][col]
            self.canvas.itemconfig(rect_id, fill=color)
        self.highlighted_cells.clear()

    def load_images(self, folderpath: str = 'figures') -> None:
        for piece, filename in PIECE_MAP.items():
            path = os.path.join(folderpath, filename)
            img = Image.open(path).convert("RGBA").resize((CELL_SIZE, CELL_SIZE))
            self.images[piece] = ImageTk.PhotoImage(img)

    def draw_board(self, first_draw=False):
        if first_draw:
            self.canvas.delete("all")
            self.board_gui = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
            for y in range(8):
                for x in range(8):
                    color = DARK_COLOR if (x + y) % 2 else LIGHT_COLOR
                    rect_id = self.canvas.create_rectangle(
                        x * CELL_SIZE, y * CELL_SIZE,
                        (x + 1) * CELL_SIZE, (y + 1) * CELL_SIZE,
                        fill=color, outline=""
                    )
                    self.board_gui[y][x] = rect_id

        # Фигуры отрисовываем всегда заново
        self.canvas.delete("piece")
        for y in range(8):
            for x in range(8):
                piece = self.logic.board[y][x]
                if piece:
                    self.canvas.create_image(
                        (x + 0.5) * CELL_SIZE, (y + 0.5) * CELL_SIZE,
                        image=self.images[piece], tags="piece"
                    )

        # Перерисовываем подсветку по верхнему уровню
        for row, col in self.highlighted_cells:
            color = DARK_COLOR if (row + col) % 2 else LIGHT_COLOR
            self.canvas.itemconfig(self.board_gui[row][col], fill=color)
            # Накладываем цвет подсветки
            for key in HIGHLIGHT_COLOR_MAP:
                if (row, col) in self.moving_params.get("legal_moves", {}).get(key, []):
                    self.canvas.itemconfig(self.board_gui[row][col], fill=HIGHLIGHT_COLOR_MAP[key])

    def draw_piece(self, piece, x, y):
        if piece and piece in self.images:
            self.canvas.create_image(
                (x + 0.5) * CELL_SIZE,
                (y + 0.5) * CELL_SIZE,
                image=self.images[piece]
            )

    def pixel_to_cell(self, x, y):
        return x // CELL_SIZE, y // CELL_SIZE

    def reverse_coords(self, x, y):
        if self.myside == 'b':
            return 7 - x, 7 - y
        return x, y


# вот это должно быть в отдельном классе, который будет обеспечивать связь с сервером
if __name__ == "__main__":
    ChessGUI()
