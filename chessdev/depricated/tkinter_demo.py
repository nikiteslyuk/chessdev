import tkinter as tk
from tkinter import Canvas, NW, CENTER
from PIL import Image, ImageTk
import chess
import os
import time

# --- Настройки ---
SQ = 96
TOP_MARGIN = 40
BOTTOM_MARGIN = 40
BOARD_SIZE = SQ * 8
CANVAS_H = BOARD_SIZE + TOP_MARGIN + BOTTOM_MARGIN
CANVAS_W = BOARD_SIZE

COL_L = "#F0D9B5"
COL_D = "#B58863"
CLR_LAST = "#0078D7"
CLR_MOVE = "#FFFF00"
CLR_CAP = "#FF0000"
CLR_CHK = "#C80000"
MASK_MATE = "#C80000"
MASK_PATT = "#808080"
ALPHA_SQ = 80

FPS = 60
ANIM_FRAMES = 12

FIGDIR = "figures"

PIECE_MAP = {
    "P": "wp.png",
    "N": "wkn.png",
    "B": "wb.png",
    "R": "wr.png",
    "Q": "wq.png",
    "K": "wk.png",
    "p": "bp.png",
    "n": "bkn.png",
    "b": "bb.png",
    "r": "br.png",
    "q": "bq.png",
    "k": "bk.png",
}


class ChessGUI(tk.Tk):
    def __init__(
        self,
        fen=None,
        my_color=None,
        flip_board=False,
        white_name="White",
        black_name="Black",
        quit_callback=None,
        username=None,
    ):
        super().__init__()
        self.title("Chess Tkinter Client")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_quit)
        self.my_color = my_color
        self.username = username
        self.flip_board = flip_board
        self.white_name = white_name
        self.black_name = black_name
        self.quit_callback = quit_callback
        self.board = chess.Board(fen) if fen else chess.Board()
        self.canvas = Canvas(
            self, width=CANVAS_W, height=CANVAS_H, bg="white", highlightthickness=0
        )
        self.canvas.pack()
        self.font = ("Helvetica", 32, "bold")
        self.label_font = ("Helvetica", 20, "bold")
        self.figures = self._load_figures()
        self._drag = {"sq": None, "img_id": None, "from": None, "piece": None}
        self._legal_moves = set()
        self._capture_moves = set()
        self._last_move = None
        self._anim = None
        self._anims = []
        self._promo_menu = None
        self._promo_callback = None
        self._game_over = False
        self.bind_events()
        self._redraw()
        self.after_id = None

    def _load_figures(self):
        figures = {}
        for k, filename in PIECE_MAP.items():
            img = Image.open(os.path.join(FIGDIR, filename)).resize(
                (SQ, SQ), Image.LANCZOS
            )
            figures[k] = ImageTk.PhotoImage(img)
        return figures

    def bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda e: self._on_quit())
        self.bind("<Key-Escape>", lambda e: self._on_quit())

    def flip(self, sq):
        f, r = chess.square_file(sq), chess.square_rank(sq)
        return chess.square(7 - f, 7 - r) if self.flip_board else sq

    def unflip(self, sq):
        f, r = chess.square_file(sq), chess.square_rank(sq)
        return chess.square(7 - f, 7 - r) if self.flip_board else sq

    def coords(self, sq):
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        r = r if self.flip_board else 7 - r
        x = f * SQ
        y = r * SQ + TOP_MARGIN
        return x, y

    def sq_from_xy(self, x, y):
        y_on_board = y - TOP_MARGIN
        if y_on_board < 0 or y_on_board >= SQ * 8:
            return None
        f = x // SQ
        r = y_on_board // SQ
        board_r = r if self.flip_board else 7 - r
        if 0 <= f < 8 and 0 <= board_r < 8:
            return chess.square(f, board_r)
        return None

    def on_press(self, event):
        if self._game_over or self._promo_menu:
            return
        sq = self.sq_from_xy(event.x, event.y)
        if sq is None:
            return
        piece = self.board.piece_at(sq)
        if (
            piece
            and (
                self.my_color is None
                or (self.my_color == "white" and piece.color == chess.WHITE)
                or (self.my_color == "black" and piece.color == chess.BLACK)
            )
            and piece.color == self.board.turn
        ):
            self._drag["sq"] = sq
            self._drag["from"] = (event.x, event.y)
            self._drag["piece"] = piece
            self._legal_moves = set()
            self._capture_moves = set()
            for mv in self.board.legal_moves:
                if mv.from_square == sq:
                    if self.board.piece_at(mv.to_square):
                        self._capture_moves.add(mv.to_square)
                    else:
                        self._legal_moves.add(mv.to_square)
        self._redraw()

    def on_drag(self, event):
        if self._drag["sq"] is None:
            return
        self._drag["img_id"] = (event.x, event.y)
        self._redraw()

    def on_release(self, event):
        if self._drag["sq"] is None:
            return
        to_sq = self.sq_from_xy(event.x, event.y)
        move = None
        for mv in self.board.legal_moves:
            if mv.from_square == self._drag["sq"] and mv.to_square == to_sq:
                move = mv
                break
        if move:
            self._start_animation(self._drag["sq"], to_sq, self._drag["piece"], move)
        self._drag = {"sq": None, "img_id": None, "from": None, "piece": None}
        self._legal_moves.clear()
        self._capture_moves.clear()
        self._redraw()

    def _start_animation(self, from_sq, to_sq, piece, move):
        start_x, start_y = self.coords(from_sq)
        end_x, end_y = self.coords(to_sq)
        self._anims.append(
            {
                "piece": piece,
                "from": from_sq,
                "to": to_sq,
                "img": self.figures[piece.symbol()],
                "sx": start_x,
                "sy": start_y,
                "ex": end_x,
                "ey": end_y,
                "step": 0,
                "move": move,
            }
        )
        self._animate_step()

    def _animate_step(self):
        need_redraw = False
        still_anim = []
        for anim in self._anims:
            anim["step"] += 1
            t = min(1, anim["step"] / ANIM_FRAMES)
            ease = 1 - (1 - t) * (1 - t)
            cur_x = int(anim["sx"] + (anim["ex"] - anim["sx"]) * ease)
            cur_y = int(anim["sy"] + (anim["ey"] - anim["sy"]) * ease)
            anim["cx"], anim["cy"] = cur_x, cur_y
            if t < 1:
                still_anim.append(anim)
            else:
                self.board.push(anim["move"])
                self._last_move = anim["move"]
                # Промо-меню (если надо)
                if (
                    anim["piece"].piece_type == chess.PAWN
                    and (
                        chess.square_rank(anim["to"]) == 0
                        or chess.square_rank(anim["to"]) == 7
                    )
                    and not anim["move"].promotion
                ):
                    self._show_promo_menu(anim["to"], anim["move"])
        self._anims = still_anim
        self._redraw()
        if self._anims:
            self.after_id = self.after(int(1000 / FPS), self._animate_step)
        else:
            self.after_id = None

    def _show_promo_menu(self, to_sq, move):
        self._promo_menu = PromoMenu(self, to_sq, move, self._on_promo_pick)
        self._promo_menu.lift()

    def _on_promo_pick(self, piece_type, move):
        move.promotion = piece_type
        self.board.push(move)
        self._last_move = move
        self._promo_menu.destroy()
        self._promo_menu = None
        self._redraw()

    def _redraw(self):
        self.canvas.delete("all")
        # Доска
        for r in range(8):
            for f in range(8):
                draw_r = r if self.flip_board else 7 - r
                x, y = f * SQ, draw_r * SQ + TOP_MARGIN
                color = COL_L if (f + r) % 2 else COL_D
                self.canvas.create_rectangle(x, y, x + SQ, y + SQ, fill=color, width=0)

        # Подсветки ходов и последнего хода
        if self._last_move:
            for sq in [self._last_move.from_square, self._last_move.to_square]:
                x, y = self.coords(sq)
                self.canvas.create_rectangle(
                    x, y, x + SQ, y + SQ, fill=CLR_LAST, stipple="gray50", width=0
                )
        for sq in self._legal_moves:
            x, y = self.coords(sq)
            self.canvas.create_rectangle(
                x, y, x + SQ, y + SQ, fill=CLR_MOVE, stipple="gray25", width=0
            )
        for sq in self._capture_moves:
            x, y = self.coords(sq)
            self.canvas.create_rectangle(
                x, y, x + SQ, y + SQ, fill=CLR_CAP, stipple="gray50", width=0
            )
        if self.board.is_check():
            ksq = self.board.king(self.board.turn)
            x, y = self.coords(ksq)
            self.canvas.create_rectangle(
                x, y, x + SQ, y + SQ, fill=CLR_CHK, stipple="gray50", width=0
            )

        # Фигуры
        positions = self.board.piece_map()
        dragging = self._drag["sq"]
        for sq, piece in positions.items():
            if sq == dragging:
                continue
            x, y = self.coords(sq)
            self.canvas.create_image(
                x, y, anchor=NW, image=self.figures[piece.symbol()]
            )
        # Анимация
        for anim in self._anims:
            self.canvas.create_image(
                anim["cx"], anim["cy"], anchor=NW, image=anim["img"]
            )
        # Dragged фигура
        if dragging and self._drag["img_id"]:
            dx, dy = self._drag["img_id"]
            self.canvas.create_image(
                dx - SQ // 2,
                dy - SQ // 2,
                anchor=NW,
                image=self.figures[self._drag["piece"].symbol()],
            )
        # Промо-меню
        if self._promo_menu:
            self._promo_menu.redraw()
        # Лейблы игроков
        self._draw_labels()

    def _draw_labels(self):
        bottom_label = self.white_name if (not self.flip_board) else self.black_name
        top_label = self.black_name if (not self.flip_board) else self.white_name
        self.canvas.create_text(
            SQ * 4,
            TOP_MARGIN // 2,
            text=top_label,
            font=self.label_font,
            fill="black",
            anchor=CENTER,
        )
        self.canvas.create_text(
            SQ * 4,
            TOP_MARGIN + SQ * 8 + BOTTOM_MARGIN // 2,
            text=bottom_label,
            font=self.label_font,
            fill="black",
            anchor=CENTER,
        )

    def _on_quit(self):
        if self.quit_callback:
            self.quit_callback()
        if self.after_id:
            self.after_cancel(self.after_id)
        self.destroy()


class PromoMenu(tk.Toplevel):
    def __init__(self, master, to_sq, move, callback):
        super().__init__(master)
        self.overrideredirect(True)
        self.transient(master)
        self.canvas = Canvas(self, width=SQ, height=SQ * 4 + 36, bg="#222")
        self.canvas.pack()
        self.callback = callback
        self.pieces = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        self.images = []
        color = "w" if master.board.turn else "b"
        y0 = 0
        for idx, p in enumerate(self.pieces):
            filename = PIECE_MAP[
                ("QNRBKNqrbn".lower()[(p - 1) + (0 if color == "w" else 6)])
            ]
            img = Image.open(os.path.join(FIGDIR, filename)).resize(
                (SQ, SQ), Image.LANCZOS
            )
            self.images.append(ImageTk.PhotoImage(img))
            self.canvas.create_image(
                0, y0, anchor=NW, image=self.images[-1], tags=f"piece{idx}"
            )
            self.canvas.tag_bind(
                f"piece{idx}", "<Button-1>", lambda e, pt=p: self.pick(pt)
            )
            y0 += SQ + 12
        # Position window over the to_sq
        x, y = master.coords(to_sq)
        gx = master.winfo_rootx() + x
        gy = master.winfo_rooty() + y + SQ
        self.geometry(f"+{gx}+{gy}")

    def pick(self, piece_type):
        self.callback(piece_type, self.master._promo_menu._move)

    def redraw(self):
        self.canvas.update()


# --- DEMO ---
if __name__ == "__main__":
    # Просто для проверки: локально без сервера!
    gui = ChessGUI(
        fen=None,
        my_color="white",
        flip_board=False,
        white_name="White",
        black_name="Black",
    )
    gui.mainloop()
