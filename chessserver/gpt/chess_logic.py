class ChessLogic:
    def __init__(self):
        # Initialize board with starting positions.
        # Board is 8x8 list of lists; row0=rank8, row7=rank1.
        self.board = [[None] * 8 for _ in range(8)]
        # Black pieces setup
        self.board[0] = list("rnbqkbnr")  # a8 through h8
        self.board[1] = ["p"] * 8  # a7 through h7 (black pawns)
        # Empty middle
        for r in range(2, 6):
            self.board[r] = [None] * 8
        # White pieces setup
        self.board[6] = ["P"] * 8  # a2 through h2 (white pawns)
        self.board[7] = list("RNBQKBNR")  # a1 through h1
        # Castling rights: use dict with keys 'K','Q','k','q'
        self.castling_rights = {"K": True, "Q": True, "k": True, "q": True}
        # En passant target square (row, col) after a pawn moves two steps
        self.en_passant_target = None
        # Halfmove counter for 50-move rule
        self.halfmove_clock = 0
        # Side to move: 'white' or 'black'
        self.turn = "white"

    def is_square_attacked(self, row, col, by_color):
        """Return True if square (row,col) is attacked by any piece of side by_color ('white' or 'black')."""
        # Pawn attacks: check from perspective of attacking side.
        if by_color == "white":
            # White pawns move up (decreasing row) and attack diagonally up-left/up-right.
            # So a white pawn at (r,c) attacks (r-1,c-1) and (r-1,c+1).
            # To see if (row,col) is attacked by a white pawn, check if a white pawn exists at (row+1,col-1) or (row+1,col+1).
            pawn_positions = [(row + 1, col - 1), (row + 1, col + 1)]
            pawn_piece = "P"
        else:
            # Black pawns move down (increasing row) and attack down-left/down-right.
            # So check if a black pawn is at (row-1,col-1) or (row-1,col+1).
            pawn_positions = [(row - 1, col - 1), (row - 1, col + 1)]
            pawn_piece = "p"
        for pr, pc in pawn_positions:
            if 0 <= pr < 8 and 0 <= pc < 8:
                if self.board[pr][pc] == pawn_piece:
                    return True
        # Knight attacks: all 8 L-shaped moves.
        knight_offsets = [
            (2, 1),
            (2, -1),
            (-2, 1),
            (-2, -1),
            (1, 2),
            (1, -2),
            (-1, 2),
            (-1, -2),
        ]
        knight_piece = "N" if by_color == "white" else "n"
        for dr, dc in knight_offsets:
            nr, nc = row + dr, col + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                if self.board[nr][nc] == knight_piece:
                    return True
        # King attacks: adjacent one square in any direction.
        king_offsets = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ]
        king_piece = "K" if by_color == "white" else "k"
        for dr, dc in king_offsets:
            nr, nc = row + dr, col + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                if self.board[nr][nc] == king_piece:
                    return True
        # Rook/Queen attacks: horizontal and vertical lines.
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        rook_piece = "R" if by_color == "white" else "r"
        queen_piece = "Q" if by_color == "white" else "q"
        for dr, dc in directions:
            nr, nc = row + dr, col + dc
            while 0 <= nr < 8 and 0 <= nc < 8:
                piece = self.board[nr][nc]
                if piece:
                    # If we find a piece in this direction
                    if piece == rook_piece or piece == queen_piece:
                        return True
                    # any piece blocks further scanning
                    break
                nr += dr
                nc += dc
        # Bishop/Queen attacks: diagonal lines.
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        bishop_piece = "B" if by_color == "white" else "b"
        queen_piece = "Q" if by_color == "white" else "q"
        for dr, dc in directions:
            nr, nc = row + dr, col + dc
            while 0 <= nr < 8 and 0 <= nc < 8:
                piece = self.board[nr][nc]
                if piece:
                    if piece == bishop_piece or piece == queen_piece:
                        return True
                    break
                nr += dr
                nc += dc
        return False

    def is_in_check(self, color):
        """Return True if the king of the given color is in check."""
        king_piece = "K" if color == "white" else "k"
        king_pos = None
        # Find the king on the board
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == king_piece:
                    king_pos = (r, c)
                    break
            if king_pos:
                break
        if not king_pos:
            return False
        # Check if enemy attacks the king's position
        enemy_color = "white" if color == "black" else "black"
        return self.is_square_attacked(king_pos[0], king_pos[1], enemy_color)

    def generate_moves(self, color=None):
        """Generate all legal moves for the given color (or current turn if color not specified).
        Returns a list of moves, where each move is a dict with keys: 'from',(row,col); 'to',(row,col); 'promotion' (if pawn promotion).
        """
        if color is None:
            color = self.turn
        moves = []
        enemy_color = "white" if color == "black" else "black"
        is_white = color == "white"
        # Iterate over all pieces of the given color
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if not piece:
                    continue
                if is_white and not piece.isupper():
                    continue
                if not is_white and not piece.islower():
                    continue
                # Determine moves based on piece type
                pt = piece.upper()
                if pt == "P":
                    if is_white:
                        # White pawn moves
                        # One step forward
                        if r - 1 >= 0 and self.board[r - 1][c] is None:
                            if r - 1 == 0:
                                # promotion moves for reaching rank 8
                                for promo in ["Q", "R", "B", "N"]:
                                    moves.append(
                                        {
                                            "from": (r, c),
                                            "to": (r - 1, c),
                                            "promotion": promo,
                                        }
                                    )
                            else:
                                moves.append(
                                    {
                                        "from": (r, c),
                                        "to": (r - 1, c),
                                        "promotion": None,
                                    }
                                )
                            # Two steps forward from starting rank
                            if r == 6 and self.board[r - 2][c] is None:
                                moves.append(
                                    {
                                        "from": (r, c),
                                        "to": (r - 2, c),
                                        "promotion": None,
                                    }
                                )
                        # Diagonal captures
                        for dc in (-1, 1):
                            nr, nc = r - 1, c + dc
                            if 0 <= nr < 8 and 0 <= nc < 8:
                                # capture opponent piece
                                if self.board[nr][nc] and self.board[nr][nc].islower():
                                    if nr == 0:
                                        # promotion capture
                                        for promo in ["Q", "R", "B", "N"]:
                                            moves.append(
                                                {
                                                    "from": (r, c),
                                                    "to": (nr, nc),
                                                    "promotion": promo,
                                                }
                                            )
                                    else:
                                        moves.append(
                                            {
                                                "from": (r, c),
                                                "to": (nr, nc),
                                                "promotion": None,
                                            }
                                        )
                                # en passant capture
                                if self.en_passant_target == (nr, nc):
                                    moves.append(
                                        {
                                            "from": (r, c),
                                            "to": (nr, nc),
                                            "promotion": None,
                                            "en_passant": True,
                                        }
                                    )
                    else:
                        # Black pawn moves
                        if r + 1 < 8 and self.board[r + 1][c] is None:
                            if r + 1 == 7:
                                # promotion
                                for promo in ["Q", "R", "B", "N"]:
                                    moves.append(
                                        {
                                            "from": (r, c),
                                            "to": (r + 1, c),
                                            "promotion": promo,
                                        }
                                    )
                            else:
                                moves.append(
                                    {
                                        "from": (r, c),
                                        "to": (r + 1, c),
                                        "promotion": None,
                                    }
                                )
                            if r == 1 and self.board[r + 2][c] is None:
                                moves.append(
                                    {
                                        "from": (r, c),
                                        "to": (r + 2, c),
                                        "promotion": None,
                                    }
                                )
                        for dc in (-1, 1):
                            nr, nc = r + 1, c + dc
                            if 0 <= nr < 8 and 0 <= nc < 8:
                                if self.board[nr][nc] and self.board[nr][nc].isupper():
                                    if nr == 7:
                                        for promo in ["Q", "R", "B", "N"]:
                                            moves.append(
                                                {
                                                    "from": (r, c),
                                                    "to": (nr, nc),
                                                    "promotion": promo,
                                                }
                                            )
                                    else:
                                        moves.append(
                                            {
                                                "from": (r, c),
                                                "to": (nr, nc),
                                                "promotion": None,
                                            }
                                        )
                                if self.en_passant_target == (nr, nc):
                                    moves.append(
                                        {
                                            "from": (r, c),
                                            "to": (nr, nc),
                                            "promotion": None,
                                            "en_passant": True,
                                        }
                                    )
                elif pt == "N":
                    # Knight moves
                    for dr, dc in [
                        (2, 1),
                        (2, -1),
                        (-2, 1),
                        (-2, -1),
                        (1, 2),
                        (1, -2),
                        (-1, 2),
                        (-1, -2),
                    ]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < 8 and 0 <= nc < 8:
                            if (
                                self.board[nr][nc] is None
                                or (is_white and self.board[nr][nc].islower())
                                or (not is_white and self.board[nr][nc].isupper())
                            ):
                                moves.append(
                                    {"from": (r, c), "to": (nr, nc), "promotion": None}
                                )
                elif pt in ("B", "R", "Q"):
                    # Sliding pieces: bishop, rook, queen
                    if pt == "B":
                        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
                    elif pt == "R":
                        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    else:  # Queen
                        directions = [
                            (-1, -1),
                            (-1, 1),
                            (1, -1),
                            (1, 1),
                            (-1, 0),
                            (1, 0),
                            (0, -1),
                            (0, 1),
                        ]
                    for dr, dc in directions:
                        nr, nc = r + dr, c + dc
                        while 0 <= nr < 8 and 0 <= nc < 8:
                            if self.board[nr][nc] is None:
                                moves.append(
                                    {"from": (r, c), "to": (nr, nc), "promotion": None}
                                )
                            else:
                                if is_white and self.board[nr][nc].islower():
                                    moves.append(
                                        {
                                            "from": (r, c),
                                            "to": (nr, nc),
                                            "promotion": None,
                                        }
                                    )
                                if not is_white and self.board[nr][nc].isupper():
                                    moves.append(
                                        {
                                            "from": (r, c),
                                            "to": (nr, nc),
                                            "promotion": None,
                                        }
                                    )
                                break  # hit a piece, stop in this direction
                            nr += dr
                            nc += dc
                elif pt == "K":
                    # King moves (one square any direction)
                    for dr, dc in [
                        (-1, -1),
                        (-1, 0),
                        (-1, 1),
                        (0, -1),
                        (0, 1),
                        (1, -1),
                        (1, 0),
                        (1, 1),
                    ]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < 8 and 0 <= nc < 8:
                            if (
                                self.board[nr][nc] is None
                                or (is_white and self.board[nr][nc].islower())
                                or (not is_white and self.board[nr][nc].isupper())
                            ):
                                moves.append(
                                    {"from": (r, c), "to": (nr, nc), "promotion": None}
                                )
                    # Castling moves
                    if is_white and r == 7 and c == 4:
                        # White king on e1
                        if (
                            self.castling_rights.get("K")
                            and self.board[7][5] is None
                            and self.board[7][6] is None
                            and self.board[7][7] == "R"
                        ):
                            # King-side: squares f1,g1 empty; rook at h1
                            if (
                                not self.is_in_check("white")
                                and not self.is_square_attacked(7, 5, "black")
                                and not self.is_square_attacked(7, 6, "black")
                            ):
                                moves.append(
                                    {
                                        "from": (7, 4),
                                        "to": (7, 6),
                                        "promotion": None,
                                        "castle": True,
                                    }
                                )
                        if (
                            self.castling_rights.get("Q")
                            and self.board[7][3] is None
                            and self.board[7][2] is None
                            and self.board[7][1] is None
                            and self.board[7][0] == "R"
                        ):
                            # Queen-side: squares d1,c1,b1 empty; rook at a1
                            if (
                                not self.is_in_check("white")
                                and not self.is_square_attacked(7, 3, "black")
                                and not self.is_square_attacked(7, 2, "black")
                            ):
                                moves.append(
                                    {
                                        "from": (7, 4),
                                        "to": (7, 2),
                                        "promotion": None,
                                        "castle": True,
                                    }
                                )
                    if not is_white and r == 0 and c == 4:
                        # Black king on e8
                        if (
                            self.castling_rights.get("k")
                            and self.board[0][5] is None
                            and self.board[0][6] is None
                            and self.board[0][7] == "r"
                        ):
                            if (
                                not self.is_in_check("black")
                                and not self.is_square_attacked(0, 5, "white")
                                and not self.is_square_attacked(0, 6, "white")
                            ):
                                moves.append(
                                    {
                                        "from": (0, 4),
                                        "to": (0, 6),
                                        "promotion": None,
                                        "castle": True,
                                    }
                                )
                        if (
                            self.castling_rights.get("q")
                            and self.board[0][3] is None
                            and self.board[0][2] is None
                            and self.board[0][1] is None
                            and self.board[0][0] == "r"
                        ):
                            if (
                                not self.is_in_check("black")
                                and not self.is_square_attacked(0, 3, "white")
                                and not self.is_square_attacked(0, 2, "white")
                            ):
                                moves.append(
                                    {
                                        "from": (0, 4),
                                        "to": (0, 2),
                                        "promotion": None,
                                        "castle": True,
                                    }
                                )
        # Filter out moves that leave own king in check (make them legal moves)
        legal_moves = []
        for move in moves:
            from_r, from_c = move["from"]
            to_r, to_c = move["to"]
            promo = move.get("promotion")
            # Save current state to restore later
            board_backup = [row[:] for row in self.board]
            rights_backup = self.castling_rights.copy()
            ep_backup = self.en_passant_target
            halfmove_backup = self.halfmove_clock
            turn_backup = self.turn
            # Apply move on the board (simulate)
            piece = self.board[from_r][from_c]
            captured = None
            is_castle = move.get("castle", False)
            is_ep = move.get("en_passant", False)
            if is_castle:
                # Move rook as well during simulation
                if to_c == 6:  # king-side castle
                    self.board[from_r][5] = self.board[from_r][7]
                    self.board[from_r][7] = None
                else:  # queen-side castle
                    self.board[from_r][3] = self.board[from_r][0]
                    self.board[from_r][0] = None
            if is_ep:
                # Remove the pawn that is captured en passant
                if is_white:
                    captured = self.board[to_r + 1][to_c]
                    self.board[to_r + 1][to_c] = None
                else:
                    captured = self.board[to_r - 1][to_c]
                    self.board[to_r - 1][to_c] = None
            else:
                captured = self.board[to_r][to_c]
            # Move the piece (handle promotion)
            if promo and piece and piece.upper() == "P":
                # Promote pawn to the chosen piece
                self.board[to_r][to_c] = promo if is_white else promo.lower()
            else:
                self.board[to_r][to_c] = piece
            self.board[from_r][from_c] = None
            # Update castling rights for simulation
            if piece:
                if piece == "K":  # white king moved
                    self.castling_rights["K"] = False
                    self.castling_rights["Q"] = False
                if piece == "k":  # black king moved
                    self.castling_rights["k"] = False
                    self.castling_rights["q"] = False
                if from_r == 7 and from_c == 7:  # white rook from h1 moved or captured
                    self.castling_rights["K"] = False
                if from_r == 7 and from_c == 0:  # white rook from a1
                    self.castling_rights["Q"] = False
                if from_r == 0 and from_c == 7:  # black rook from h8
                    self.castling_rights["k"] = False
                if from_r == 0 and from_c == 0:  # black rook from a8
                    self.castling_rights["q"] = False
            # If pawn moved two, set en passant target for simulation
            new_ep = None
            if piece and piece.upper() == "P" and abs(to_r - from_r) == 2:
                new_ep = ((from_r + to_r) // 2, from_c)
            self.en_passant_target = new_ep
            # halfmove_clock and turn not needed for check simulation
            # Check if own king is in check after this move
            if not self.is_in_check(color):
                legal_moves.append(move)
            # Restore state
            self.board = [row[:] for row in board_backup]
            self.castling_rights = rights_backup
            self.en_passant_target = ep_backup
            self.halfmove_clock = halfmove_backup
            self.turn = turn_backup
        return legal_moves

    def make_move(self, from_row, from_col, to_row, to_col, promotion=None):
        """Make the move on the board (assumes it is legal). Returns a dict describing the move."""
        piece = self.board[from_row][from_col]
        if not piece:
            return None
        color = "white" if piece.isupper() else "black"
        # Determine special move types
        is_castle = piece.upper() == "K" and abs(to_col - from_col) == 2
        is_en_passant = False
        if (
            piece.upper() == "P"
            and self.en_passant_target == (to_row, to_col)
            and self.board[to_row][to_col] is None
        ):
            is_en_passant = True
        # Handle capture removal
        captured_piece = None
        if is_en_passant:
            if color == "white":
                captured_piece = self.board[to_row + 1][to_col]
                self.board[to_row + 1][to_col] = None
            else:
                captured_piece = self.board[to_row - 1][to_col]
                self.board[to_row - 1][to_col] = None
        else:
            captured_piece = self.board[to_row][to_col]
        # Handle castling rook move
        if is_castle:
            if to_col == 6:  # king-side
                self.board[from_row][5] = self.board[from_row][7]
                self.board[from_row][7] = None
            else:  # queen-side
                self.board[from_row][3] = self.board[from_row][0]
                self.board[from_row][0] = None
        # Move the piece (with promotion if applicable)
        if promotion and piece.upper() == "P" and (to_row == 0 or to_row == 7):
            # Use the promotion choice (e.g. 'Q','R','B','N')
            new_piece = promotion if color == "white" else promotion.lower()
            self.board[to_row][to_col] = new_piece
        else:
            self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = None
        # Update castling rights after move
        if piece == "K":
            self.castling_rights["K"] = False
            self.castling_rights["Q"] = False
        if piece == "k":
            self.castling_rights["k"] = False
            self.castling_rights["q"] = False
        if from_row == 7 and from_col == 7:  # white rook from h1 moved
            self.castling_rights["K"] = False
        if from_row == 7 and from_col == 0:  # white rook from a1 moved
            self.castling_rights["Q"] = False
        if from_row == 0 and from_col == 7:  # black rook from h8 moved
            self.castling_rights["k"] = False
        if from_row == 0 and from_col == 0:  # black rook from a8 moved
            self.castling_rights["q"] = False
        # If a rook was captured, update castling rights for that rook
        if captured_piece == "R":  # a white rook was captured
            if to_row == 7 and to_col == 0:  # white queen-side rook captured
                self.castling_rights["Q"] = False
            if to_row == 7 and to_col == 7:  # white king-side rook captured
                self.castling_rights["K"] = False
        if captured_piece == "r":  # a black rook was captured
            if to_row == 0 and to_col == 0:
                self.castling_rights["q"] = False
            if to_row == 0 and to_col == 7:
                self.castling_rights["k"] = False
        # Update en passant target after move
        if piece.upper() == "P" and abs(to_row - from_row) == 2:
            self.en_passant_target = ((from_row + to_row) // 2, from_col)
        else:
            self.en_passant_target = None
        # Update halfmove clock
        if piece.upper() == "P" or captured_piece:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        # Flip the turn to the other side
        self.turn = "black" if color == "white" else "white"
        # Return details of the move
        return {
            "from": (from_row, from_col),
            "to": (to_row, to_col),
            "piece": piece,
            "captured": captured_piece,
            "promotion": promotion,
            "castle": is_castle,
            "en_passant": is_en_passant,
        }
