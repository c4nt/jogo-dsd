import socket
import threading
import sys
import utils
import time

# --- ESTADO GLOBAL DO JOGO ---
game_state = {
    "p1_nome": "Eu", 
    "p2_nome": "Inimigo",
    "p1_hp": 3, 
    "p2_hp": 3,
    "p1_acao": "IDLE", 
    "p2_acao": "IDLE",
    "flecha_x": -1, 
    "flecha_y": -1,
    "my_role": "IDLE"  # NOVO: Guarda se sou "ATK" (Atacante) ou "DEF" (Defensor)
}

running = True

def renderizar():
    """Desenha a tela usando o utils"""
    utils.limpar_tela()
    utils.mostrar_titulo()
    utils.desenhar_arena(
        game_state["p1_nome"], game_state["p1_hp"], game_state["p1_acao"],
        game_state["p2_nome"], game_state["p2_hp"], game_state["p2_acao"],
        game_state["flecha_x"], game_state["flecha_y"]
    )

def udp_listener(sock):
    """Escuta dados rápidos de animação (UDP)"""
    while running:
        try:
            data, _ = sock.recvfrom(utils.BUFFER_SIZE)
            msg = data.decode()
            if msg.startswith(utils.CMD_ANIMATION):
                # Formato: ANIM:X:Y
                _, x, y = msg.split(":")
                game_state["flecha_x"] = int(x)
                game_state["flecha_y"] = int(y)
                renderizar()
        except: 
            break

def main():
    global running, game_state
    utils.limpar_tela()
    
    # --- 1. CONEXÃO INICIAL ---
    print("--- CONECTAR ---")
    ip = input("IP do Servidor: ")
    nome = input("Seu Nickname: ")
    
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.settimeout(5.0) # Timeout para não travar se IP estiver errado
    try:
        tcp.connect((ip, utils.TCP_PORT))
        tcp.settimeout(None) # Volta ao normal
        tcp.send(nome.encode())
    except Exception as e:
        print(f"Erro ao conectar: {e}")
        print("Verifique o IP e o Firewall do servidor.")
        return

    # --- 2. LOBBY (SALA DE ESPERA) ---
    in_lobby = True
    while in_lobby:
        utils.limpar_tela()
        print(f"Bem-vindo, {nome}!")
        print("1. Criar nova sala")
        print("2. Listar salas e Entrar")
        op = input("Opção: ")
        
        if op == '1':
            tcp.send(utils.CMD_CREATE.encode())
            resp = tcp.recv(utils.BUFFER_SIZE).decode()
            if resp == utils.CMD_WAIT:
                print("Sala criada! Aguardando oponente entrar...")
                in_lobby = False # Vai para o loop do jogo esperar o START
        
        elif op == '2':
            tcp.send(utils.CMD_LIST.encode())
            try:
                lista = tcp.recv(utils.BUFFER_SIZE).decode()
                print("\n" + lista)
                rid = input("Digite o ID da sala (ou ENTER para voltar): ")
                if rid:
                    tcp.send(f"{utils.CMD_JOIN}:{rid}".encode())
                    # Espera confirmação JOIN_OK
                    resp = tcp.recv(utils.BUFFER_SIZE).decode()
                    
                    if resp == "JOIN_OK":
                        print("Entrando na sala...")
                        in_lobby = False
                    elif resp.startswith(utils.CMD_ERROR):
                        print(f"Erro: {resp}")
                        time.sleep(2)
            except:
                print("Erro ao comunicar com lobby.")
                break

    # --- 3. SETUP UDP ---
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Tenta abrir porta UDP. Se der erro (ex: rodando 2 clientes no mesmo PC), avisa mas continua.
    try:
        udp.bind(('0.0.0.0', utils.UDP_PORT))
    except:
        print("Aviso: Porta UDP ocupada. A animação pode não funcionar neste cliente se for local.")
    
    threading.Thread(target=udp_listener, args=(udp,), daemon=True).start()

    # --- 4. LOOP DO JOGO (PARTIDA) ---
    while running:
        try:
            # Fica travado aqui esperando mensagem do servidor (START ou RESULT)
            msg = tcp.recv(utils.BUFFER_SIZE).decode()
            if not msg: break
            
            # --- CASO A: INÍCIO DO JOGO ---
            if msg.startswith(utils.CMD_START):
                # Msg: START:NomeOponente:SeuID:ROLE
                parts = msg.split(":")
                op_nome = parts[1]
                my_id = parts[2]
                role = parts[3] # "ATK" ou "DEF"
                
                game_state['my_role'] = role
                
                if my_id == '1':
                    game_state['p1_nome'] = nome
                    game_state['p2_nome'] = op_nome
                else:
                    game_state['p1_nome'] = op_nome
                    game_state['p2_nome'] = nome
                
                print(f"\nJOGO INICIADO! Papel inicial: {role}")
                time.sleep(2)
                renderizar()
                
            # --- CASO B: RESULTADO DO TURNO ---
            elif msg.startswith(utils.CMD_RESULT):
                # Msg: RESULT:HP1:HP2:STATUS:NEXT_ROLE
                parts = msg.split(":")
                game_state['p1_hp'] = int(parts[1])
                game_state['p2_hp'] = int(parts[2])
                status = parts[3]
                next_role = parts[4] # O que serei no próximo turno
                
                game_state['my_role'] = next_role
                game_state['flecha_x'] = -1 # Reseta animação
                renderizar()
                
                if status == "WIN":
                    print("\n\n>>> VOCÊ VENCEU! <<<"); running = False
                elif status == "LOSE":
                    print("\n\n>>> GAME OVER... <<<"); running = False
                elif status == "DRAW":
                    print("\n\n>>> EMPATE! <<<"); running = False

            # --- SE O JOGO CONTINUA, É HORA DE JOGAR ---
            if running:
                # Mostra instrução baseada no papel (Atacar ou Defender)
                acao_txt = "ATACAR (Sua vez de atirar!)" if game_state['my_role'] == "ATK" else "DEFENDER (Proteja-se!)"
                print(f"\n--- {acao_txt} ---")
                
                if game_state['my_role'] == "ATK":
                    print(f"Onde mirar? ({utils.PART_HEAD}, {utils.PART_TORSO}, {utils.PART_LEGS})")
                else:
                    print(f"Onde posicionar o escudo? ({utils.PART_HEAD}, {utils.PART_TORSO}, {utils.PART_LEGS})")
                
                # Validação do Input
                valid = False
                while not valid:
                    escolha = input(">> ").upper()
                    if "CAB" in escolha: escolha = utils.PART_HEAD; valid = True
                    elif "TRO" in escolha: escolha = utils.PART_TORSO; valid = True
                    elif "PER" in escolha: escolha = utils.PART_LEGS; valid = True
                    else: print("Opção inválida. Tente CABECA, TRONCO ou PERNAS.")
                
                # Atualiza visual localmente para feedback imediato
                is_p1 = (game_state['p1_nome'] == nome)
                if is_p1: game_state['p1_acao'] = escolha
                else: game_state['p2_acao'] = escolha
                renderizar()
                
                print("Aguardando oponente...")
                tcp.send(f"{utils.CMD_CHOICE}:{escolha}".encode())
                
                # O loop reinicia e volta para o tcp.recv esperando o resultado

        except Exception as e:
            print(f"Erro ou desconexão: {e}")
            break
            
    tcp.close()
    udp.close()
    print("Fim da execução.")

if __name__ == "__main__":
    main()
