#!/usr/bin/env python3
import os, sys, random, pygame, chess

# ── настройки ───────────────────────────────────────────────
SQ, FPS, FIGDIR = 96, 60, "figures"
COL_L, COL_D = (240, 217, 181), (181, 136, 99)
CLR_LAST, CLR_MOVE, CLR_CAP, CLR_CHK = (
    (0, 120, 215, 120),
    (255, 255, 0, 120),
    (255, 0, 0, 120),
    (200, 0, 0, 150),
)
MASK_MATE, MASK_PATT = (200, 0, 0, 130), (128, 128, 128, 130)
ANIM_FRAMES = 12

pygame.init()
screen = pygame.display.set_mode((SQ * 8, SQ * 8))
pygame.display.set_caption("Chess client")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 64)

MAP = {
    chess.PAWN: "p",
    chess.KNIGHT: "kn",
    chess.BISHOP: "b",
    chess.ROOK: "r",
    chess.QUEEN: "q",
    chess.KING: "k",
}
SPR = {}
for col, prefix in ((chess.WHITE, "w"), (chess.BLACK, "b")):
    for pt, s in MAP.items():
        path = os.path.join(FIGDIR, f"{prefix}{s}.png")
        SPR[(col, pt)] = pygame.transform.smoothscale(
            pygame.image.load(path).convert_alpha(), (SQ, SQ)
        )


def surf(color):
    s = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
    s.fill(color)
    return s


S_LAST, S_MOVE, S_CAP, S_CHK = map(surf, (CLR_LAST, CLR_MOVE, CLR_CAP, CLR_CHK))


def sq_center(sq):
    f, r = chess.square_file(sq), 7 - chess.square_rank(sq)
    return f * SQ + SQ // 2, r * SQ + SQ // 2


def mouse_sq(x, y):
    f, r = x // SQ, 7 - (y // SQ)
    return chess.square(f, r) if 0 <= f < 8 and 0 <= r < 8 else None


class Anim:
    def __init__(self, ptype, col, start, target, orig):
        self.ptype, self.col, self.pos = ptype, col, start
        self.start, self.target, self.orig, self.f = start, target, orig, 0

    def tick(self):
        self.f += 1
        t = min(1, self.f / ANIM_FRAMES)
        ease = 1 - (1 - t) * (1 - t)
        self.pos = (
            self.start[0] + (self.target[0] - self.start[0]) * ease,
            self.start[1] + (self.target[1] - self.start[1]) * ease,
        )
        return t >= 1


class PromoMenu:
    def __init__(self, col, to_sq):
        self.col = col
        self.opts = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        w = h = SQ
        pad = 12
        H = h * 4 + pad * 3
        f, r = chess.square_file(to_sq), 7 - chess.square_rank(to_sq)
        x = f * SQ
        y = r * SQ + SQ if r * SQ + SQ + H <= SQ * 8 else r * SQ - H
        self.rects = []
        self.top = (x, y)
        self.surf = pygame.Surface((w, H), pygame.SRCALPHA)
        self.surf.fill((30, 30, 30, 230))
        for i, pt in enumerate(self.opts):
            self.surf.blit(SPR[(col, pt)], (0, i * (h + pad)))
            self.rects.append(pygame.Rect(x, y + i * (h + pad), w, h))

    def draw(self):
        screen.blit(self.surf, self.top)

    def click(self, p):
        for r, pt in zip(self.rects, self.opts):
            if r.collidepoint(p):
                return pt
        return None


# ── логика ──────────────────────────────────────────────────
board = chess.Board()
drag_sq = drag_pos = None
legal_sqs, capture_sqs = set(), set()
last = None
anims = []
pending = None
promo = None
game_over = False

# Жёсткий сценарий: конь, пешка, слон, рокировка
script_moves = [
    chess.Move.from_uci("g8f6"),  # 1… ♞g8–f6
    chess.Move.from_uci("e7e6"),  # 2… e7–e6 (открываем слона)
    chess.Move.from_uci("f8d6"),  # 3… ♝f8–d6
    chess.Move.from_uci("e8g8"),  # 4… 0–0
]
script_stage = 0  # сколько выполнено


def push_clear(mv):
    global last, pending, promo, legal_sqs, capture_sqs
    board.push(mv)
    last = mv
    pending = None
    legal_sqs.clear()
    capture_sqs.clear()


def result_text():
    if board.is_checkmate():
        return (
            "Мат. Белые победили"
            if board.turn == chess.BLACK
            else "Мат. Чёрные победили"
        )
    return "Пат. Ничья"


running = True
while running:
    dt = clock.tick(FPS)
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

        if game_over:  # блок ввода после конца партии
            continue

        # ── меню промоции ──
        if promo:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                ptype = promo.click(e.pos)
                if ptype:
                    pending.promotion = ptype
                    push_clear(pending)
                    promo = None
                    pending = None
            continue

        if anims:
            continue  # пока идёт анимация

        # ── взаимодействие ──
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            sq = mouse_sq(*e.pos)
            if (
                sq is not None
                and board.piece_at(sq)
                and board.piece_at(sq).color == board.turn
            ):
                drag_sq, drag_pos = sq, e.pos
                legal_sqs, capture_sqs = set(), set()
                for mv in board.legal_moves:
                    if mv.from_square == sq:
                        (
                            capture_sqs if board.piece_at(mv.to_square) else legal_sqs
                        ).add(mv.to_square)
        elif e.type == pygame.MOUSEMOTION and drag_sq:
            drag_pos = e.pos
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and drag_sq:
            dst = mouse_sq(*e.pos)
            mv = None
            for m in board.legal_moves:
                if m.from_square == drag_sq and m.to_square == dst:
                    mv = m
                    break
            start = (drag_pos[0] - SQ // 2, drag_pos[1] - SQ // 2)
            tgt = (
                (sq_center(dst)[0] - SQ // 2, sq_center(dst)[1] - SQ // 2)
                if mv
                else (sq_center(drag_sq)[0] - SQ // 2, sq_center(drag_sq)[1] - SQ // 2)
            )
            anims.append(
                Anim(
                    board.piece_at(drag_sq).piece_type, board.turn, start, tgt, drag_sq
                )
            )
            if mv and board.is_castling(mv):
                rf, rt = (7, 5) if chess.square_file(mv.to_square) == 6 else (0, 3)
                rf, rt = chess.square(
                    rf, chess.square_rank(mv.to_square)
                ), chess.square(rt, chess.square_rank(mv.to_square))
                rs, rtg = sq_center(rf), sq_center(rt)
                rook = board.piece_at(rf)
                anims.append(
                    Anim(
                        rook.piece_type,
                        rook.color,
                        (rs[0] - SQ // 2, rs[1] - SQ // 2),
                        (rtg[0] - SQ // 2, rtg[1] - SQ // 2),
                        rf,
                    )
                )
            pending = mv
            drag_sq = drag_pos = None
            legal_sqs.clear()
            capture_sqs.clear()

    # ── анимация ──
    if anims:
        if all(a.tick() for a in anims):
            anims.clear()
            if pending:
                # если это превращение — только показываем меню (push только после выбора)
                if board.piece_at(
                    pending.from_square
                ).piece_type == chess.PAWN and chess.square_rank(pending.to_square) in (
                    0,
                    7,
                ):
                    promo = PromoMenu(board.turn, pending.to_square)
                    # push делаем после выбора!
                else:
                    push_clear(pending)
                    pending = None
    elif promo and pending:
        # ждём, когда пользователь выберет фигуру превращения (push будет там)
        pass
    else:
        # ── ход бота ──
        if not board.turn and not promo and not board.is_game_over():
            mv = None
            while script_stage < len(script_moves):
                candidate = script_moves[script_stage]
                if candidate in board.legal_moves:
                    mv = candidate
                    script_stage += 1
                    break
                else:
                    break  # Если не доступен, ждём
            if mv is None and script_stage < len(script_moves):
                # Ждём возможности для следующего хода из скрипта
                pass
            else:
                if mv is None:
                    mv = random.choice(list(board.legal_moves))
            if mv:
                s, t = sq_center(mv.from_square), sq_center(mv.to_square)
                anims.append(
                    Anim(
                        board.piece_at(mv.from_square).piece_type,
                        board.turn,
                        (s[0] - SQ // 2, s[1] - SQ // 2),
                        (t[0] - SQ // 2, t[1] - SQ // 2),
                        mv.from_square,
                    )
                )
                if board.is_castling(mv):
                    rf, rt = (7, 5) if chess.square_file(mv.to_square) == 6 else (0, 3)
                    rf, rt = chess.square(
                        rf, chess.square_rank(mv.to_square)
                    ), chess.square(rt, chess.square_rank(mv.to_square))
                    rs, rtg = sq_center(rf), sq_center(rt)
                    rook = board.piece_at(rf)
                    anims.append(
                        Anim(
                            rook.piece_type,
                            rook.color,
                            (rs[0] - SQ // 2, rs[1] - SQ // 2),
                            (rtg[0] - SQ // 2, rtg[1] - SQ // 2),
                            rf,
                        )
                    )
                pending = mv

    # ── проверяем конец партии ──
    if board.is_game_over() and not game_over:
        game_over = True
        legal_sqs.clear()
        capture_sqs.clear()

    # ── отрисовка ──────────────────────────────────────────────
    for r in range(8):
        for f in range(8):
            pygame.draw.rect(
                screen,
                COL_L if (f + r) & 1 else COL_D,
                pygame.Rect(f * SQ, r * SQ, SQ, SQ),
            )
    if not game_over:
        if not legal_sqs and not capture_sqs and last:
            for sq in (last.from_square, last.to_square):
                f, r = chess.square_file(sq), 7 - chess.square_rank(sq)
                screen.blit(S_LAST, (f * SQ, r * SQ))
        for s in legal_sqs:
            f, r = chess.square_file(s), 7 - chess.square_rank(s)
            screen.blit(S_MOVE, (f * SQ, r * SQ))
        for s in capture_sqs:
            f, r = chess.square_file(s), 7 - chess.square_rank(s)
            screen.blit(S_CAP, (f * SQ, r * SQ))
        if board.is_check():
            k = board.king(board.turn)
            f, r = chess.square_file(k), 7 - chess.square_rank(k)
            screen.blit(S_CHK, (f * SQ, r * SQ))

    anim_orig = {a.orig for a in anims}
    promo_pending = promo is not None and pending is not None

    for sq, p in board.piece_map().items():
        # Не рисуем перетаскиваемую фигуру и анимируемые
        if sq == drag_sq or sq in anim_orig:
            continue
        # В момент меню превращения не рисуем жертву и не рисуем исходную пешку
        if promo_pending:
            if sq == pending.to_square:
                # Не рисуем жертву (если взятие)
                if board.piece_at(sq) and board.piece_at(pending.from_square):
                    if (
                        board.piece_at(sq).color
                        != board.piece_at(pending.from_square).color
                    ):
                        continue
            if sq == pending.from_square:
                # Не рисуем пешку на исходной клетке
                continue
        f, r = chess.square_file(sq), 7 - chess.square_rank(sq)
        screen.blit(SPR[(p.color, p.piece_type)], (f * SQ, r * SQ))

    # --- В момент меню превращения рисуем пешку на to_square ---
    if promo_pending:
        p = board.piece_at(pending.from_square)
        f, r = chess.square_file(pending.to_square), 7 - chess.square_rank(
            pending.to_square
        )
        screen.blit(SPR[(p.color, p.piece_type)], (f * SQ, r * SQ))

    for a in anims:
        screen.blit(SPR[(a.col, a.ptype)], a.pos)
    if drag_sq and drag_pos:
        p = board.piece_at(drag_sq)
        screen.blit(
            SPR[(p.color, p.piece_type)], (drag_pos[0] - SQ // 2, drag_pos[1] - SQ // 2)
        )
    if promo:
        promo.draw()

    if game_over:  # полумаска + текст
        mask = pygame.Surface((SQ * 8, SQ * 8), pygame.SRCALPHA)
        mask.fill(MASK_MATE if board.is_checkmate() else MASK_PATT)
        screen.blit(mask, (0, 0))
        txt = result_text()
        img = font.render(txt, True, (255, 255, 255))
        rect = img.get_rect(center=(SQ * 4, SQ * 4))
        screen.blit(img, rect)

    pygame.display.flip()

pygame.quit()
