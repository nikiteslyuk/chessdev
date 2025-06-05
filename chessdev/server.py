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


class ChessServer:
    def __init__(self):
        self.users = {}  # name -> Player
        self.tables = {}  # id -> Table
        self.table_id_seq = 1
        self.lock = asyncio.Lock()  # Асинхронный лок

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

                elif cmd["action"] == "create":
                    color = cmd["color"]
                    async with self.lock:
                        tid = self.table_id_seq
                        self.table_id_seq += 1
                        table = Table(tid)
                        if color == "white":
                            table.white = user
                        elif color == "black":
                            table.black = user
                        self.tables[tid] = table
                        resp["data"] = {"table_id": tid}
                        resp["msg"] = f"Table {tid} created, waiting for second player"

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
                            }
                            for t in self.tables.values()
                        ]
                        resp["data"] = tables

                elif cmd["action"] == "join":
                    tid = cmd["table_id"]
                    color = cmd["color"]
                    async with self.lock:
                        if tid not in self.tables:
                            resp["status"] = "err"
                            resp["msg"] = "No such table"
                        else:
                            t = self.tables[tid]
                            if color == "white":
                                if t.white:
                                    resp["status"] = "err"
                                    resp["msg"] = "White is taken"
                                else:
                                    t.white = user
                            else:
                                if t.black:
                                    resp["status"] = "err"
                                    resp["msg"] = "Black is taken"
                                else:
                                    t.black = user
                            resp["msg"] = f"You joined table {tid} as {color}"

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
                elif cmd['action'] == 'quit_table':
                    tid, color, user = cmd['table_id'], cmd['color'], cmd['user']
                    async with self.lock:
                        if tid in self.tables:
                            t = self.tables[tid]
                            if color == 'white' and t.white == user:
                                t.white = None
                            elif color == 'black' and t.black == user:
                                t.black = None
                            # Если оба ушли, удалить стол
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
