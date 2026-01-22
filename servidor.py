import socket
import threading
import time
import utils

class Room:
    def __init__(self, room_id, host_sock, host_addr, host_name):
        self.id = room_id
        self.players = [
            {'sock': host_sock, 'addr': host_addr, 'name': host_name, 'hp': 3},
            None # Player 2 entra depois
        ]
        self.turn_data = {}
    
    def is_full(self):
        return self.players[1] is not None

class GameServer:
    def __init__(self):
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.bind(('0.0.0.0', utils.TCP_PORT))
        self.tcp_sock.listen()
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        self.rooms = {} # Dict de salas {id: Room}
        self.room_counter = 1
        print(f"Servidor rodando na porta TCP {utils.TCP_PORT}")

    def start(self):
        while True:
            client, addr = self.tcp_sock.accept()
            threading.Thread(target=self.handle_client_lobby, args=(client, addr)).start()

    def handle_client_lobby(self, client, addr):
        try:
            # 1. Login
            name = client.recv(utils.BUFFER_SIZE).decode()
            print(f"Player conectado: {name} de {addr}")

            # 2. Loop do Lobby (Criar/Listar/Entrar)
            in_lobby = True
            current_room = None

            while in_lobby:
                msg = client.recv(utils.BUFFER_SIZE).decode()
                
                if msg == utils.CMD_CREATE:
                    # Cria sala
                    rid = str(self.room_counter)
                    self.room_counter += 1
                    new_room = Room(rid, client, addr, name)
                    self.rooms[rid] = new_room
                    current_room = new_room
                    
                    client.send(utils.CMD_WAIT.encode())
                    in_lobby = False # Sai do lobby, vai esperar jogo
                    
                elif msg == utils.CMD_LIST:
                    # Monta lista
                    lista = "SALAS DISPONIVEIS:\n"
                    if not self.rooms:
                        lista += "(Nenhuma sala criada. Crie uma!)"
                    else:
                        for rid, room in self.rooms.items():
                            status = "CHEIA" if room.is_full() else "AGUARDANDO"
                            lista += f"ID [{rid}] - Host: {room.players[0]['name']} ({status})\n"
                    client.send(lista.encode())
                    
                elif msg.startswith(utils.CMD_JOIN):
                    # Tenta entrar: JOIN:ID
                    _, rid = msg.split(":")
                    if rid in self.rooms and not self.rooms[rid].is_full():
                        room = self.rooms[rid]
                        room.players[1] = {'sock': client, 'addr': addr, 'name': name, 'hp': 3}
                        current_room = room
                        in_lobby = False
                        
                        # Inicia o jogo para ambos
                        self.start_game(room)
                    else:
                        client.send(f"{utils.CMD_ERROR}:Sala cheia ou inexistente.".encode())

            # Se saiu do lobby e criou sala, fica esperando P2
            if current_room and current_room.players[1] is None:
                # Loop de espera passiva (a thread do P2 vai disparar o start_game)
                pass 

        except Exception as e:
            print(f"Erro no lobby: {e}")

    def start_game(self, room):
        print(f"Iniciando Jogo na Sala {room.id}")
        p1 = room.players[0]
        p2 = room.players[1]
        
        # Avisa P1
        p1['sock'].send(f"{utils.CMD_START}:{p2['name']}:1".encode())
        # Avisa P2
        p2['sock'].send(f"{utils.CMD_START}:{p1['name']}:2".encode())
        
        # Inicia loop da partida
        threading.Thread(target=self.game_loop, args=(room,)).start()

    def game_loop(self, room):
        running = True
        while running:
            try:
                # Limpa dados do turno anterior
                room.turn_data = {}
                
                # Recebe P1
                msg1 = room.players[0]['sock'].recv(utils.BUFFER_SIZE).decode()
                self.process_choice(room, 0, msg1)
                
                # Recebe P2
                msg2 = room.players[1]['sock'].recv(utils.BUFFER_SIZE).decode()
                self.process_choice(room, 1, msg2)
                
                # Resolve
                self.resolve_turn(room)
                
                # Checa Morte
                if room.players[0]['hp'] <= 0 or room.players[1]['hp'] <= 0:
                    running = False
                    # Remove sala da lista global
                    if room.id in self.rooms: del self.rooms[room.id]
                    
            except Exception as e:
                print(f"Erro na sala {room.id}: {e}")
                running = False

    def process_choice(self, room, idx, msg):
        if msg.startswith(utils.CMD_CHOICE):
            room.turn_data[idx] = msg.split(":")[1]

    def resolve_turn(self, room):
        p1_ch = room.turn_data[0]
        p2_ch = room.turn_data[1]
        
        # P1 Ataca P2 (Simples: se mirou onde não defendeu, dano)
        # Para ser justo, vamos fazer P1 ataca P2 E P2 ataca P1 no mesmo turno?
        # Ou um ataca e outro defende?
        # REGRA ATUALIZADA: Quem ataca? Vamos fazer "Ambos Atiram". 
        # Se P1 Atira Cabeça e P2 Defende Cabeça -> Defendeu.
        # Se P1 Atira Cabeça e P2 Defende Perna -> P2 Toma Dano.
        
        # Dano em P2?
        if p1_ch != p2_ch: room.players[1]['hp'] -= 1
        # Dano em P1? (P2 também atirou no P1?)
        # Pela sua regra: "Um atacando e um defendendo". 
        # Vamos assumir alternância? Turno 1: P1 Ataca. Turno 2: P2 Ataca.
        # OU: Ambos são arqueiros, ambos atiram ao mesmo tempo. 
        # VOU MANTER: Ambos atiram e defendem ao mesmo tempo (mais dinâmico).
        if p2_ch != p1_ch: room.players[0]['hp'] -= 1
        
        # Animação UDP (Duas flechas se cruzando!)
        self.stream_arrows(room, p1_ch, p2_ch)
        
        # Envia Estado
        hp1 = room.players[0]['hp']
        hp2 = room.players[1]['hp']
        
        status1 = "WIN" if hp2 <= 0 else "LOSE" if hp1 <= 0 else "NEXT"
        status2 = "WIN" if hp1 <= 0 else "LOSE" if hp2 <= 0 else "NEXT"
        
        # Se ambos morrerem ao mesmo tempo: EMPATE (DRAW)
        if hp1 <= 0 and hp2 <= 0: status1 = status2 = "DRAW"

        room.players[0]['sock'].send(f"{utils.CMD_RESULT}:{hp1}:{hp2}:{status1}".encode())
        room.players[1]['sock'].send(f"{utils.CMD_RESULT}:{hp1}:{hp2}:{status2}".encode())

    def stream_arrows(self, room, target1, target2):
        # Manda pacotes UDP
        for i in range(10, 50, 2):
            # Flecha P1 -> P2 (Esq -> Dir)
            y1 = 2 if target1 == utils.PART_HEAD else 3 if target1 == utils.PART_TORSO else 4
            msg1 = f"{utils.CMD_ANIMATION}:{i}:{y1}"
            
            # Flecha P2 -> P1 (Dir -> Esq) - opcional, mas legal visualmente
            # Simplificando: vamos mandar só a flecha do P1 para testar primeiro
            
            self.udp_sock.sendto(msg1.encode(), (room.players[0]['addr'][0], utils.UDP_PORT))
            self.udp_sock.sendto(msg1.encode(), (room.players[1]['addr'][0], utils.UDP_PORT))
            time.sleep(0.05)

if __name__ == "__main__":
    GameServer().start()
