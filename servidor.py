import socket
import threading
import time
import utils

class Room:
    def __init__(self, room_id, host_sock, host_addr, host_name):
        self.id = room_id
        self.players = [
            {'sock': host_sock, 'addr': host_addr, 'name': host_name, 'hp': 3},
            None
        ]
        self.turn_data = {}
        self.attacker_idx = 0 

    def is_full(self): return self.players[1] is not None

class GameServer:
    def __init__(self):
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.bind(('0.0.0.0', utils.TCP_PORT))
        self.tcp_sock.listen()
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rooms = {} 
        self.room_counter = 1
        print(f"Servidor rodando na porta TCP {utils.TCP_PORT}")

    def start(self):
        while True:
            client, addr = self.tcp_sock.accept()
            threading.Thread(target=self.handle_client_lobby, args=(client, addr)).start()

    def handle_client_lobby(self, client, addr):
        try:
            name = client.recv(utils.BUFFER_SIZE).decode()
            print(f"Conexão: {name} {addr}")
            in_lobby = True
            current_room = None

            while in_lobby:
                msg = client.recv(utils.BUFFER_SIZE).decode()
                
                if msg == utils.CMD_CREATE:
                    rid = str(self.room_counter)
                    self.room_counter += 1
                    new_room = Room(rid, client, addr, name)
                    self.rooms[rid] = new_room
                    current_room = new_room
                    client.send(utils.CMD_WAIT.encode())
                    in_lobby = False 
                    
                elif msg == utils.CMD_LIST:
                    lista = "SALAS:\n"
                    for rid, room in self.rooms.items():
                        s = "CHEIA" if room.is_full() else "LIVRE"
                        lista += f"[{rid}] {room.players[0]['name']} ({s})\n"
                    client.send((lista or "Nenhuma sala").encode())
                    
                elif msg.startswith(utils.CMD_JOIN):
                    _, rid = msg.split(":")
                    if rid in self.rooms and not self.rooms[rid].is_full():
                        room = self.rooms[rid]
                        room.players[1] = {'sock': client, 'addr': addr, 'name': name, 'hp': 3}
                        current_room = room
                        in_lobby = False
                        client.send("JOIN_OK".encode())
                        time.sleep(0.1)
                        self.start_game(room)
                    else:
                        client.send(f"{utils.CMD_ERROR}:Erro ao entrar".encode())

            if current_room and current_room.players[1] is None: pass 

        except Exception as e: print(f"Erro lobby: {e}")

    def start_game(self, room):
        p1 = room.players[0]; p2 = room.players[1]
        p1['sock'].send(f"{utils.CMD_START}:{p2['name']}:1:ATK".encode())
        p2['sock'].send(f"{utils.CMD_START}:{p1['name']}:2:DEF".encode())
        threading.Thread(target=self.game_loop, args=(room,)).start()

    def game_loop(self, room):
        running = True
        while running:
            try:
                room.turn_data = {}
                # Recebe jogadas (sem ordem)
                m1 = room.players[0]['sock'].recv(utils.BUFFER_SIZE).decode()
                self.process_choice(room, 0, m1)
                m2 = room.players[1]['sock'].recv(utils.BUFFER_SIZE).decode()
                self.process_choice(room, 1, m2)
                
                if len(room.turn_data) == 2: self.resolve_turn(room)
                
                if room.players[0]['hp'] <= 0 or room.players[1]['hp'] <= 0:
                    running = False
                    if room.id in self.rooms: del self.rooms[room.id]
            except: running = False

    def process_choice(self, room, idx, msg):
        if msg.startswith(utils.CMD_CHOICE): room.turn_data[idx] = msg.split(":")[1]

    def resolve_turn(self, room):
        atk = room.attacker_idx; def_idx = 1 - atk
        if room.turn_data[atk] != room.turn_data[def_idx]:
            room.players[def_idx]['hp'] -= 1
        
        # Define trajeto
        if atk == 0: start, end = 9, 51
        else:        start, end = 51, 9

        self.stream_arrow(room, start, end, room.turn_data[atk])

        room.attacker_idx = 1 - atk
        roles = ["ATK" if room.attacker_idx == 0 else "DEF", 
                 "ATK" if room.attacker_idx == 1 else "DEF"]

        hp1 = room.players[0]['hp']; hp2 = room.players[1]['hp']
        s1 = "WIN" if hp2<=0 else "LOSE" if hp1<=0 else "NEXT"
        s2 = "WIN" if hp1<=0 else "LOSE" if hp2<=0 else "NEXT"
        if hp1<=0 and hp2<=0: s1=s2="DRAW"

        room.players[0]['sock'].send(f"{utils.CMD_RESULT}:{hp1}:{hp2}:{s1}:{roles[0]}".encode())
        room.players[1]['sock'].send(f"{utils.CMD_RESULT}:{hp1}:{hp2}:{s2}:{roles[1]}".encode())

    def stream_arrow(self, room, start, end, height_code):
        # Define direção e caractere da flecha
        if start < end:
            step = 2
            arrow_char = '>' # Indo pra direita
        else:
            step = -2
            arrow_char = '<' # Indo pra esquerda (voltando)
        
        y = 4
        if height_code == utils.PART_HEAD: y = 2
        elif height_code == utils.PART_TORSO: y = 3
        
        for x in range(start, end, step):
            # NOVO: Envia também o arrow_char
            msg = f"{utils.CMD_ANIMATION}:{x}:{y}:{arrow_char}"
            for p in room.players:
                self.udp_sock.sendto(msg.encode(), (p['addr'][0], utils.UDP_PORT))
            time.sleep(0.04)

if __name__ == "__main__":
    GameServer().start()
