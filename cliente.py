import socket
import threading
import sys
import utils
import time

game_state = {
    "p1_nome": "Eu", "p2_nome": "Inimigo",
    "p1_hp": 3, "p2_hp": 3,
    "p1_acao": "IDLE", "p2_acao": "IDLE",
    "flecha_x": -1, "flecha_y": -1,
    "flecha_char": ">", # NOVO: Guarda a direção da flecha
    "my_role": "IDLE"
}
running = True

def renderizar():
    utils.limpar_tela()
    utils.mostrar_titulo()
    # Passamos o flecha_char aqui
    utils.desenhar_arena(
        game_state["p1_nome"], game_state["p1_hp"], game_state["p1_acao"],
        game_state["p2_nome"], game_state["p2_hp"], game_state["p2_acao"],
        game_state["flecha_x"], game_state["flecha_y"], game_state["flecha_char"]
    )

def udp_listener(sock):
    while running:
        try:
            data, _ = sock.recvfrom(utils.BUFFER_SIZE)
            msg = data.decode()
            if msg.startswith(utils.CMD_ANIMATION):
                # Formato NOVO: ANIM:X:Y:CHAR
                parts = msg.split(":")
                game_state["flecha_x"] = int(parts[1])
                game_state["flecha_y"] = int(parts[2])
                if len(parts) > 3:
                    game_state["flecha_char"] = parts[3]
                renderizar()
        except: break

def main():
    global running, game_state
    utils.limpar_tela()
    
    print("--- CONECTAR ---")
    ip = input("IP do Servidor: ")
    nome = input("Seu Nickname: ")
    
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.settimeout(5.0)
    try:
        tcp.connect((ip, utils.TCP_PORT))
        tcp.settimeout(None)
        tcp.send(nome.encode())
    except Exception as e:
        print(f"Erro: {e}"); return

    # --- LOBBY ---
    in_lobby = True
    while in_lobby:
        utils.limpar_tela()
        print(f"Bem-vindo, {nome}!")
        print("1. Criar sala\n2. Listar e Entrar")
        op = input("Opção: ")
        
        if op == '1':
            tcp.send(utils.CMD_CREATE.encode())
            if tcp.recv(utils.BUFFER_SIZE).decode() == utils.CMD_WAIT:
                print("Aguardando..."); in_lobby = False
        elif op == '2':
            tcp.send(utils.CMD_LIST.encode())
            print(tcp.recv(utils.BUFFER_SIZE).decode())
            rid = input("ID Sala: ")
            if rid:
                tcp.send(f"{utils.CMD_JOIN}:{rid}".encode())
                resp = tcp.recv(utils.BUFFER_SIZE).decode()
                if resp == "JOIN_OK": in_lobby = False
                else: print(resp); time.sleep(2)

    # --- UDP ---
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: udp.bind(('0.0.0.0', utils.UDP_PORT))
    except: print("UDP Ocupado (Erro visual)")
    threading.Thread(target=udp_listener, args=(udp,), daemon=True).start()

    # --- JOGO ---
    while running:
        try:
            msg = tcp.recv(utils.BUFFER_SIZE).decode()
            if not msg: break
            
            if msg.startswith(utils.CMD_START):
                _, op, mid, role = msg.split(":")
                game_state['my_role'] = role
                if mid == '1': game_state['p1_nome'] = nome; game_state['p2_nome'] = op
                else:          game_state['p1_nome'] = op; game_state['p2_nome'] = nome
                renderizar()
                
            elif msg.startswith(utils.CMD_RESULT):
                parts = msg.split(":")
                game_state['p1_hp'] = int(parts[1])
                game_state['p2_hp'] = int(parts[2])
                game_state['my_role'] = parts[4]
                game_state['flecha_x'] = -1 
                renderizar()
                
                if parts[3] == "WIN": print("VITORIA!"); running = False
                elif parts[3] == "LOSE": print("DERROTA!"); running = False
                elif parts[3] == "DRAW": print("EMPATE!"); running = False

            if running:
                txt = "ATACAR" if game_state['my_role'] == "ATK" else "DEFENDER"
                print(f"\n--- {txt} ({utils.PART_HEAD}, {utils.PART_TORSO}, {utils.PART_LEGS}) ---")
                
                valid = False
                while not valid:
                    op = input(">> ").upper()
                    if "CAB" in op: ch = utils.PART_HEAD; valid = True
                    elif "TRO" in op: ch = utils.PART_TORSO; valid = True
                    elif "PER" in op: ch = utils.PART_LEGS; valid = True
                
                if game_state['p1_nome'] == nome: game_state['p1_acao'] = ch
                else: game_state['p2_acao'] = ch
                renderizar()
                print("Aguardando...")
                tcp.send(f"{utils.CMD_CHOICE}:{ch}".encode())

        except: break
    tcp.close(); udp.close()

if __name__ == "__main__":
    main()
