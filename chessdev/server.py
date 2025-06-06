import asyncio
import pickle
import chess

HOST = "0.0.0.0"
PORT = 5555


class Player:
    def __init__(self, name):
        self.name = name


class Table:
    def __init__(self, tid, white=None, black=None):
        self.id = tid
        self.white = white
        self.black = black
        self.board = chess.Board()
        self.spectators = []
        self.active_players = set()


class ChessServer:
    def __init__(self):
        self.users = {}
        self.tables = {}
        self.table_id_seq = 1
        self.lock = asyncio.Lock()

    async def handle(self, reader, writer):
        user = None
        try:
            while True:
                data_len_bytes = await reader.readexactly(4)
                data_len = int.from_bytes(data_len_bytes, "big")
                data = await reader.readexactly(data_len)
                cmd = pickle.loads(data)
                resp = {"status": "ok", "msg": None, "data": None}

                if cmd["action"] == "register":
                    name = cmd["name"]
                    async with self.lock:
                        if name in self.users:
                            resp["status"] = "err"
                            resp["msg"] = "Name taken"
                        else:
                            self.users[name] = Player(name)
                            resp["msg"] = f"Welcome, {name}"
                            user = name

                elif cmd["action"] == "ready_play":
                    tid = cmd["table_id"]
                    user = cmd["user"]
                    async with self.lock:
                        if tid not in self.tables:
                            resp["status"] = "err"
                            resp["msg"] = "No such table"
                        else:
                            t = self.tables[tid]
                            t.active_players.add(user)
                            resp["msg"] = f"{user} is ready"

                elif cmd["action"] == "createtable":
                    color = cmd.get("color", None)
                    async with self.lock:
                        existing_ids = set(self.tables.keys())
                        tid = 1
                        while tid in existing_ids:
                            tid += 1
                        table = Table(tid)
                        import random
                        if color is None:
                            color = random.choice(["white", "black"])
                        if color == "white":
                            table.white = user
                        elif color == "black":
                            table.black = user
                        self.tables[tid] = table
                        resp["data"] = {"table_id": tid, "color": color}
                        resp["msg"] = f"Table {tid} created, you play as {color}, waiting for second player"

                elif cmd["action"] == "list_tables":
                    async with self.lock:
                        tables = [
                            {
                                "id": t.id,
                                "white": t.white,
                                "black": t.black,
                                "in_game": (
                                    t.white is not None and t.black is not None
                                ),
                                "active_players": list(t.active_players) if hasattr(t, "active_players") else []
                            }
                            for t in self.tables.values()
                        ]
                        resp["data"] = tables

                elif cmd["action"] == "join":
                    tid = cmd.get("table_id", None)
                    async with self.lock:
                        if tid is None:
                            found = False
                            for t in self.tables.values():
                                if not (t.white and t.black):
                                    found = True
                                    if not t.white:
                                        t.white = user
                                        color = "white"
                                    else:
                                        t.black = user
                                        color = "black"
                                    resp["data"] = {"table_id": t.id, "color": color}
                                    resp["msg"] = f"Fastjoined to table {t.id} as {color}"
                                    break
                            if not found:
                                resp["status"] = "err"
                                resp["msg"] = "No available tables. Create one!"
                        else:
                            if tid not in self.tables:
                                resp["status"] = "err"
                                resp["msg"] = "No such table"
                            else:
                                t = self.tables[tid]
                                color = None
                                if not t.white:
                                    t.white = user
                                    color = "white"
                                elif not t.black:
                                    t.black = user
                                    color = "black"
                                else:
                                    resp["status"] = "err"
                                    resp["msg"] = "Both seats are taken"
                                    color = None
                                if color:
                                    resp["msg"] = f"You joined table {tid} as {color}"
                                    resp["data"] = {"color": color}


                elif cmd["action"] == "move":
                    tid, uci = cmd["table_id"], cmd["uci"]
                    async with self.lock:
                        if tid not in self.tables:
                            resp["status"] = "err"
                            resp["msg"] = "No such table"
                        else:
                            t = self.tables[tid]
                            mv = chess.Move.from_uci(uci)
                            if mv in t.board.legal_moves:
                                t.board.push(mv)
                                resp["msg"] = "Move accepted"
                            else:
                                resp["status"] = "err"
                                resp["msg"] = "Illegal move"

                elif cmd["action"] == "get_board":
                    tid = cmd["table_id"]
                    async with self.lock:
                        if tid not in self.tables:
                            resp["status"] = "err"
                            resp["msg"] = "No such table"
                        else:
                            t = self.tables[tid]
                            resp["data"] = t.board.fen()

                elif cmd["action"] == "view":
                    tid = cmd["table_id"]
                    async with self.lock:
                        if tid not in self.tables:
                            resp["status"] = "err"
                            resp["msg"] = "No such table"
                        else:
                            t = self.tables[tid]
                            resp["data"] = t.board.fen()
                elif cmd['action'] == 'leave':
                    tid, color, user = cmd['table_id'], cmd['color'], cmd['user']
                    async with self.lock:
                        if tid in self.tables:
                            t = self.tables[tid]
                            if color == 'white' and t.white == user:
                                t.white = None
                            elif color == 'black' and t.black == user:
                                t.black = None
                            if t.white is None and t.black is None:
                                del self.tables[tid]
                            resp['msg'] = f"{user} left table {tid} ({color})"
                        else:
                            resp['status'] = 'err'
                            resp['msg'] = 'No such table'

                out_data = pickle.dumps(resp)
                writer.write(len(out_data).to_bytes(4, "big"))
                writer.write(out_data)
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        finally:
            if user is not None:
                async with self.lock:
                    if user in self.users:
                        del self.users[user]
            writer.close()
            await writer.wait_closed()


async def main():
    server = ChessServer()

    async def handle_conn(reader, writer):
        await server.handle(reader, writer)

    srv = await asyncio.start_server(handle_conn, HOST, PORT)
    print(f"Async server listening on {HOST}:{PORT}")
    async with srv:
        await srv.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
