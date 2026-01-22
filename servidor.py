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
        self.attacker_idx = 0 # 0 = Player 1 começa atacando, 1 = Player 2 começa

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

                        client.send("JOIN_OK".encode())  # <--- LINHA NOVA
                        time.sleep(0.1)                  # <--- LINHA NOVA
                        
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
        
        # Avisa P1 (ID 1) que ele começa ATACANDO (ATK)
        p1['sock'].send(f"{utils.CMD_START}:{p2['name']}:1:ATK".encode())
        # Avisa P2 (ID 2) que ele começa DEFENDENDO (DEF)
        p2['sock'].send(f"{utils.CMD_START}:{p1['name']}:2:DEF".encode())
        
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
        idx_atk = room.attacker_idx
        idx_def = 1 - idx_atk 
        
        atk_choice = room.turn_data[idx_atk]
        def_choice = room.turn_data[idx_def]
        
        # Lógica de Dano
        if atk_choice != def_choice:
            room.players[idx_def]['hp'] -= 1
        
        # --- DEFININDO A DIREÇÃO DA FLECHA ---
        if idx_atk == 0:
            # P1 Ataca (Esquerda -> Direita)
            start_x = 8   # Sai da arma do P1
            end_x = 52    # Vai até o corpo do P2
        else:
            # P2 Ataca (Direita -> Esquerda)
            start_x = 52  # Sai da arma do P2
            end_x = 8     # Vai até o corpo do P1

        # Chama a animação com os pontos corretos
        self.stream_arrow(room, start_x, end_x, atk_choice)

        # Prepara próximo turno (Inverte papéis)
        room.attacker_idx = 1 - room.attacker_idx 
        next_role_p1 = "ATK" if room.attacker_idx == 0 else "DEF"
        next_role_p2 = "ATK" if room.attacker_idx == 1 else "DEF"

        # Envia Resultados
        hp1 = room.players[0]['hp']
        hp2 = room.players[1]['hp']
        status1 = "WIN" if hp2 <= 0 else "LOSE" if hp1 <= 0 else "NEXT"
        status2 = "WIN" if hp1 <= 0 else "LOSE" if hp2 <= 0 else "NEXT"

        room.players[0]['sock'].send(f"{utils.CMD_RESULT}:{hp1}:{hp2}:{status1}:{next_role_p1}".encode())
        room.players[1]['sock'].send(f"{utils.CMD_RESULT}:{hp1}:{hp2}:{status2}:{next_role_p2}".encode())   

    def stream_arrow(self, room, start, end, height_code):
        # --- O SEGREDO ESTÁ AQUI ---
        # Se o inicio for menor que o fim, passo positivo (vai pra frente)
        # Se o inicio for maior que o fim, passo negativo (vai pra tras)
        step = 2 if start < end else -2
        
        # Define altura Y
        y = 4 # Pernas
        if height_code == utils.PART_HEAD: y = 2
        elif height_code == utils.PART_TORSO: y = 3
        
        # O range precisa do passo correto
        for x in range(start, end, step):
            msg = f"{utils.CMD_ANIMATION}:{x}:{y}"
            
            # Manda para os dois jogadores
            for p in room.players:
                self.udp_sock.sendto(msg.encode(), (p['addr'][0], utils.UDP_PORT))
            
            # Velocidade da animação
            time.sleep(0.04)

if __name__ == "__main__":
    GameServer().start()
