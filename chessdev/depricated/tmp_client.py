import socket
import pickle
import cmd
import shlex
import sys
import time
import pygame
import os
import chess

SERVER = '127.0.0.1'
PORT = 5555

def send_recv(sock, data):
    payload = pickle.dumps(data)
    sock.sendall(len(payload).to_bytes(4, 'big') + payload)
    resp_len_bytes = sock.recv(4)
    if not resp_len_bytes:
        raise ConnectionError("Server disconnected")
    resp_len = int.from_bytes(resp_len_bytes, 'big')
    resp_data = b''
    while len(resp_data) < resp_len:
        chunk = sock.recv(resp_len - len(resp_data))
        if not chunk:
            raise ConnectionError("Server disconnected")
        resp_data += chunk
    return pickle.loads(resp_data)

def get_table_info(sock, table_id):
    resp = send_recv(sock, {'action': 'list_tables'})
    for t in resp['data']:
        if t['id'] == table_id:
            return t
    return None

def play_game_pygame(table_id, sock, my_color=None, flip_board=False, quit_callback=None, username=None):
    SQ, FPS, FIGDIR = 96, 120, "figures"
    COL_L, COL_D = (240,217,181), (181,136,99)
    CLR_LAST, CLR_MOVE, CLR_CAP, CLR_CHK = (0,120,215,120), (255,255,0,120), (255,0,0,120), (200,0,0,150)
    MASK_MATE, MASK_PATT = (200,0,0,130), (128,128,128,130)
    ANIM_FRAMES = 12

    pygame.init()
    screen = pygame.display.set_mode((SQ*8, SQ*8 + 60))
    pygame.display.set_caption(f"Table {table_id}")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 48)
    label_font = pygame.font.SysFont(None, 40)

    MAP = {chess.PAWN:"p",chess.KNIGHT:"kn",chess.BISHOP:"b",
           chess.ROOK:"r",chess.QUEEN:"q",chess.KING:"k"}
    SPR={}
    for col,prefix in ((chess.WHITE,"w"),(chess.BLACK,"b")):
        for pt,s in MAP.items():
            path=os.path.join(FIGDIR,f"{prefix}{s}.png")
            SPR[(col,pt)] = pygame.transform.smoothscale(pygame.image.load(path).convert_alpha(),(SQ,SQ))

    def surf(color):
        s=pygame.Surface((SQ,SQ),pygame.SRCALPHA); s.fill(color); return s
    S_LAST,S_MOVE,S_CAP,S_CHK = map(surf,(CLR_LAST,CLR_MOVE,CLR_CAP,CLR_CHK))

    def sq_center(sq):
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        r = r if flip_board else 7 - r
        return f*SQ+SQ//2, r*SQ+SQ//2

    def mouse_sq(x,y):
        if y >= SQ*8: return None
        f = x // SQ
        r = y // SQ
        board_r = r if flip_board else 7 - r
        if 0 <= f < 8 and 0 <= board_r < 8:
            return chess.square(f, board_r)
        return None

    class Anim:
        def __init__(self,ptype,col,start,target,orig):
            self.ptype, self.col, self.pos = ptype,col,start
            self.start,self.target,self.orig,self.f = start,target,orig,0
        def tick(self):
            self.f+=1; t=min(1,self.f/ANIM_FRAMES); ease=1-(1-t)*(1-t)
            self.pos=( self.start[0]+(self.target[0]-self.start[0])*ease,
                       self.start[1]+(self.target[1]-self.start[1])*ease )
            return t>=1

    class PromoMenu:
        def __init__(self,col,to_sq):
            self.col=col; self.opts=[chess.QUEEN,chess.ROOK,chess.BISHOP,chess.KNIGHT]
            w=h=SQ; pad=12; H=h*4+pad*3
            f,r=chess.square_file(to_sq),chess.square_rank(to_sq)
            r_p = r if flip_board else 7 - r
            x=f*SQ; y=r_p*SQ+SQ if r_p*SQ+SQ+H<=SQ*8 else r_p*SQ-H
            self.rects=[]; self.top=(x,y)
            self.surf=pygame.Surface((w,H),pygame.SRCALPHA); self.surf.fill((30,30,30,230))
            for i,pt in enumerate(self.opts):
                self.surf.blit(SPR[(col,pt)],(0,i*(h+pad)))
                self.rects.append(pygame.Rect(x,y+i*(h+pad),w,h))
        def draw(self): screen.blit(self.surf,self.top)
        def click(self,p):
            for r,pt in zip(self.rects,self.opts):
                if r.collidepoint(p): return pt
            return None

    # Board state and anim queue
    resp = send_recv(sock, {'action': 'get_board', 'table_id': table_id})
    if resp['status'] != 'ok':
        print("Ошибка: нет такой партии!")
        pygame.quit()
        return

    board = chess.Board(resp['data'])
    drag_sq=drag_pos=None
    legal_sqs,capture_sqs=set(),set()
    last=None
    anims=[]; pending=None; promo=None; game_over=False

    prev_board_fen = board.fen()
    need_anim = False

    my_is_white = (my_color == 'white')
    my_is_black = (my_color == 'black')
    my_is_player = (my_is_white or my_is_black)

    # Для вывода имен игроков
    def draw_labels(table_info):
        # Верх (opponent/black для white, white для black)
        opp_name = None
        my_name = username if username else (my_color or '')
        if table_info:
            if my_color == 'white':
                opp_name = table_info.get('black')
            elif my_color == 'black':
                opp_name = table_info.get('white')
            else:
                opp_name = None
            if not opp_name:
                opp_name = "Оппонент вышел, ждем следующего"
        else:
            opp_name = ""
        if flip_board:
            top_label = my_name
            bottom_label = opp_name
        else:
            top_label = opp_name
            bottom_label = my_name
        # Верхний
        if top_label:
            top_text = label_font.render(str(top_label), True, (0,0,0))
            top_rect = top_text.get_rect(center=(SQ*4, 24))
            screen.blit(top_text, top_rect)
        # Нижний
        if bottom_label:
            bottom_text = label_font.render(str(bottom_label), True, (0,0,0))
            bottom_rect = bottom_text.get_rect(center=(SQ*4, SQ*8+36))
            screen.blit(bottom_text, bottom_rect)

    def reload_board(with_anim=True):
        nonlocal board, last, legal_sqs, capture_sqs, promo, pending, anims, game_over, prev_board_fen, need_anim
        resp = send_recv(sock, {'action': 'get_board', 'table_id': table_id})
        new_board = chess.Board(resp['data'])
        # Находим ход, чтобы отобразить анимацию
        if with_anim and board.fen() != new_board.fen():
            move = None
            for mv in board.legal_moves:
                test_board = board.copy()
                test_board.push(mv)
                if test_board.fen() == new_board.fen():
                    move = mv
                    break
            if move:
                s, t = sq_center(move.from_square), sq_center(move.to_square)
                anims.append(Anim(board.piece_at(move.from_square).piece_type, board.turn, (s[0]-SQ//2, s[1]-SQ//2), (t[0]-SQ//2, t[1]-SQ//2), move.from_square))
                if board.is_castling(move):
                    rf, rt = ((7,5) if chess.square_file(move.to_square)==6 else (0,3))
                    rf, rt = chess.square(rf, chess.square_rank(move.to_square)), chess.square(rt, chess.square_rank(move.to_square))
                    rs, rtg = sq_center(rf), sq_center(rt)
                    rook = board.piece_at(rf)
                    anims.append(Anim(rook.piece_type, rook.color, (rs[0]-SQ//2, rs[1]-SQ//2), (rtg[0]-SQ//2, rtg[1]-SQ//2), rf))
            else:
                # Если не нашли ход — просто обновляем
                pass
        prev_board_fen = board.fen()
        board.set_fen(new_board.fen())
        last = None
        legal_sqs.clear(); capture_sqs.clear()
        pending = None; promo = None; #anims.clear()
        game_over = board.is_game_over()
        need_anim = False

    running = True
    while running:
        dt=clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running=False
                if quit_callback: quit_callback()
            if e.type == pygame.KEYDOWN and (e.key == pygame.K_ESCAPE):
                running = False
                if quit_callback: quit_callback()
            if game_over:
                continue
            if promo:
                if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                    ptype=promo.click(e.pos)
                    if ptype:
                        pending.promotion=ptype
                        uci = pending.uci()
                        resp = send_recv(sock, {'action':'move', 'table_id':table_id, 'uci':uci})
                        if resp['status'] == 'ok':
                            reload_board(with_anim=True)
                        promo=None
                        pending=None
                continue
            if anims: continue
            if my_is_player and ((board.turn and my_is_white) or (not board.turn and my_is_black)):
                if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                    sq=mouse_sq(*e.pos)
                    if sq is not None and board.piece_at(sq) and board.piece_at(sq).color==board.turn:
                        drag_sq,drag_pos=sq,e.pos
                        legal_sqs,capture_sqs=set(),set()
                        for mv in board.legal_moves:
                            if mv.from_square==sq:
                                (capture_sqs if board.piece_at(mv.to_square) else legal_sqs).add(mv.to_square)
                elif e.type==pygame.MOUSEMOTION and drag_sq:
                    drag_pos=e.pos
                elif e.type==pygame.MOUSEBUTTONUP and e.button==1 and drag_sq:
                    dst=mouse_sq(*e.pos); mv=None
                    for m in board.legal_moves:
                        if m.from_square==drag_sq and m.to_square==dst: mv=m; break
                    start=(drag_pos[0]-SQ//2,drag_pos[1]-SQ//2)
                    tgt=(sq_center(dst)[0]-SQ//2,sq_center(dst)[1]-SQ//2) if mv else \
                        (sq_center(drag_sq)[0]-SQ//2,sq_center(drag_sq)[1]-SQ//2)
                    anims.append(Anim(board.piece_at(drag_sq).piece_type,board.turn,start,tgt,drag_sq))
                    if mv and board.is_castling(mv):
                        rf,rt = ((7,5) if chess.square_file(mv.to_square)==6 else (0,3))
                        rf,rt=chess.square(rf,chess.square_rank(mv.to_square)),chess.square(rt,chess.square_rank(mv.to_square))
                        rs,rtg=sq_center(rf),sq_center(rt)
                        rook=board.piece_at(rf)
                        anims.append(Anim(rook.piece_type,rook.color,(rs[0]-SQ//2,rs[1]-SQ//2),(rtg[0]-SQ//2,rtg[1]-SQ//2),rf))
                    pending=mv
                    drag_sq=drag_pos=None
                    legal_sqs.clear(); capture_sqs.clear()

        # --- Анимация входящего хода ---
        if anims:
            if all(a.tick() for a in anims):
                anims.clear()
                if pending:
                    # если это превращение — только показываем меню (push только после выбора)
                    if board.piece_at(pending.from_square).piece_type==chess.PAWN and chess.square_rank(pending.to_square) in (0,7):
                        promo=PromoMenu(board.turn,pending.to_square)
                        # push делаем после выбора!
                    else:
                        if pending:
                            # Если это наш ход — отправляем
                            uci = pending.uci()
                            resp = send_recv(sock, {'action':'move', 'table_id':table_id, 'uci':uci})
                            if resp['status'] == 'ok':
                                reload_board(with_anim=True)
                            pending=None
        elif promo and pending:
            # ждём, когда пользователь выберет фигуру превращения (push будет там)
            pass
        else:
            # Проверка входящих ходов — poll, и если FEN изменился, проиграть анимацию!
            resp = send_recv(sock, {'action': 'get_board', 'table_id': table_id})
            new_fen = resp['data']
            if new_fen != board.fen():
                # Найдём входящий ход и анимируем
                new_board = chess.Board(new_fen)
                move = None
                for mv in board.legal_moves:
                    test_board = board.copy()
                    test_board.push(mv)
                    if test_board.fen() == new_fen:
                        move = mv
                        break
                if move:
                    s, t = sq_center(move.from_square), sq_center(move.to_square)
                    anims.append(Anim(board.piece_at(move.from_square).piece_type, board.turn, (s[0]-SQ//2, s[1]-SQ//2), (t[0]-SQ//2, t[1]-SQ//2), move.from_square))
                    if board.is_castling(move):
                        rf, rt = ((7,5) if chess.square_file(move.to_square)==6 else (0,3))
                        rf, rt = chess.square(rf, chess.square_rank(move.to_square)), chess.square(rt, chess.square_rank(move.to_square))
                        rs, rtg = sq_center(rf), sq_center(rt)
                        rook = board.piece_at(rf)
                        anims.append(Anim(rook.piece_type, rook.color, (rs[0]-SQ//2, rs[1]-SQ//2), (rtg[0]-SQ//2, rtg[1]-SQ//2), rf))
                    pending = None
                board.set_fen(new_fen)
            time.sleep(0.1)

        # --- Отрисовка
        screen.fill((255,255,255))
        for r in range(8):
            for f in range(8):
                draw_r = r if flip_board else 7-r
                pygame.draw.rect(screen, COL_L if (f+r)&1 else COL_D, pygame.Rect(f*SQ,draw_r*SQ,SQ,SQ))
        if not game_over:
            if not legal_sqs and not capture_sqs and last:
                for sq in (last.from_square,last.to_square):
                    f,r=chess.square_file(sq),chess.square_rank(sq)
                    draw_r = r if flip_board else 7 - r
                    screen.blit(S_LAST,(f*SQ,draw_r*SQ))
            for s in legal_sqs:
                f,r=chess.square_file(s),chess.square_rank(s)
                draw_r = r if flip_board else 7 - r
                screen.blit(S_MOVE,(f*SQ,draw_r*SQ))
            for s in capture_sqs:
                f,r=chess.square_file(s),chess.square_rank(s)
                draw_r = r if flip_board else 7 - r
                screen.blit(S_CAP,(f*SQ,draw_r*SQ))
            if board.is_check():
                k=board.king(board.turn)
                f,r=chess.square_file(k),chess.square_rank(k)
                draw_r = r if flip_board else 7 - r
                screen.blit(S_CHK,(f*SQ,draw_r*SQ))
        anim_orig = {a.orig for a in anims}
        promo_pending = promo is not None and pending is not None
        for sq, p in board.piece_map().items():
            if sq == drag_sq or sq in anim_orig:
                continue
            if promo_pending:
                if sq == pending.to_square:
                    if board.piece_at(sq) and board.piece_at(pending.from_square):
                        if board.piece_at(sq).color != board.piece_at(pending.from_square).color:
                            continue
                if sq == pending.from_square:
                    continue
            f, r = chess.square_file(sq), chess.square_rank(sq)
            draw_r = r if flip_board else 7 - r
            screen.blit(SPR[(p.color, p.piece_type)], (f * SQ, draw_r * SQ))
        if promo_pending:
            p = board.piece_at(pending.from_square)
            f, r = chess.square_file(pending.to_square), chess.square_rank(pending.to_square)
            draw_r = r if flip_board else 7 - r
            screen.blit(SPR[(p.color, p.piece_type)], (f * SQ, draw_r * SQ))
        for a in anims:
            screen.blit(SPR[(a.col, a.ptype)], a.pos)
        if drag_sq and drag_pos:
            p = board.piece_at(drag_sq)
            f, r = chess.square_file(drag_sq), chess.square_rank(drag_sq)
            draw_r = r if flip_board else 7 - r
            screen.blit(SPR[(p.color, p.piece_type)], (drag_pos[0] - SQ // 2, drag_pos[1] - SQ // 2))
        if promo:
            promo.draw()
        if game_over:
            mask=pygame.Surface((SQ*8,SQ*8),pygame.SRCALPHA)
            mask.fill(MASK_MATE if board.is_checkmate() else MASK_PATT)
            screen.blit(mask,(0,0))
            txt="Мат. Белые победили" if board.turn==chess.BLACK else \
                ("Мат. Чёрные победили" if board.is_checkmate() else "Пат. Ничья")
            img=font.render(txt,True,(255,255,255))
            rect=img.get_rect(center=(SQ*4,SQ*4))
            screen.blit(img,rect)

        # --- Нарисовать лейблы имён игроков ---
        table_info = get_table_info(sock, table_id)
        draw_labels(table_info)
        pygame.display.flip()

    pygame.quit()
    return

class ChessCmd(cmd.Cmd):
    prompt = ">> "

    def __init__(self, username):
        super().__init__()
        self.sock = socket.create_connection((SERVER, PORT))
        self.username = username
        resp = send_recv(self.sock, {'action': 'register', 'name': self.username})
        if resp['status'] != 'ok':
            print("Ошибка регистрации:", resp['msg'])
            sys.exit(1)
        self.current_table = None
        self.current_color = None
        self.playing = False

    def wait_for_opponent_and_start(self):
        print("Ожидание второго игрока...")
        while True:
            resp = send_recv(self.sock, {'action': 'list_tables'})
            for t in resp['data']:
                if t['id'] == self.current_table and t['white'] and t['black']:
                    print("Партия стартует!")
                    flip = (self.current_color == 'black')
                    play_game_pygame(self.current_table, self.sock, my_color=self.current_color, flip_board=flip, quit_callback=self.on_quit_table, username=self.username)
                    self.playing = False
                    self.current_table = None
                    self.current_color = None
                    return
            time.sleep(1)

    def do_create(self, arg):
        args = shlex.split(arg)
        if not args or args[0] not in ('white', 'black'):
            print("Укажите цвет: white или black")
            return
        resp = send_recv(self.sock, {'action': 'create', 'color': args[0]})
        print(resp['msg'])
        if resp['status'] == 'ok':
            self.current_table = resp['data']['table_id']
            self.current_color = args[0]
            self.wait_for_opponent_and_start()

    def do_list(self, arg):
        resp = send_recv(self.sock, {'action': 'list_tables'})
        for t in resp['data']:
            print(f"Table {t['id']} | White: {t['white']} | Black: {t['black']} | InGame: {t['in_game']}")

    def do_join(self, arg):
        args = shlex.split(arg)
        if len(args) < 2:
            print("Пример: join 1 white")
            return
        resp = send_recv(self.sock, {'action': 'join', 'table_id': int(args[0]), 'color': args[1]})
        print(resp['msg'])
        if resp['status'] == 'ok':
            self.current_table = int(args[0])
            self.current_color = args[1]
            self.wait_for_opponent_and_start()

    def on_quit_table(self):
        if self.current_table is not None:
            send_recv(self.sock, {'action': 'quit_table', 'table_id': self.current_table, 'color': self.current_color, 'user': self.username})
            self.current_table = None
            self.current_color = None
            self.playing = False
            print("Вы покинули стол.")

    def do_quit_table(self, arg):
        'quit_table -- выйти со стола'
        self.on_quit_table()

    def do_view(self, arg):
        args = shlex.split(arg)
        if not args:
            print("Укажите номер стола")
            return
        table_id = int(args[0])
        play_game_pygame(table_id, self.sock, my_color=None, flip_board=False, username=self.username)

    def do_quit(self, arg):
        print("Выход...")
        self.on_quit_table()
        return True

    def complete_join(self, text, line, begidx, endidx):
        resp = send_recv(self.sock, {'action': 'list_tables'})
        ids = [str(t['id']) for t in resp['data']]
        return [i for i in ids if i.startswith(text)]

    def complete_create(self, text, line, begidx, endidx):
        return [c for c in ['white', 'black'] if c.startswith(text)]

    def complete_view(self, text, line, begidx, endidx):
        resp = send_recv(self.sock, {'action': 'list_tables'})
        ids = [str(t['id']) for t in resp['data']]
        return [i for i in ids if i.startswith(text)]

if __name__ == '__main__':
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("Использование: python client.py <имя_пользователя>")
        sys.exit(1)
    ChessCmd(sys.argv[1].strip()).cmdloop()
