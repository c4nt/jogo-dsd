import socket
import threading
import sys
import utils
import time

# Estado Global
game_state = {
    "p1_nome": "Eu", "p2_nome": "Inimigo",
    "p1_hp": 3, "p2_hp": 3,
    "p1_acao": "IDLE", "p2_acao": "IDLE",
    "flecha_x": -1, "flecha_y": -1
}
running = True

def renderizar():
    utils.limpar_tela()
    utils.mostrar_titulo()
    utils.desenhar_arena(
        game_state["p1_nome"], game_state["p1_hp"], game_state["p1_acao"],
        game_state["p2_nome"], game_state["p2_hp"], game_state["p2_acao"],
        game_state["flecha_x"], game_state["flecha_y"]
    )

def udp_listener(sock):
    while running:
        try:
            data, _ = sock.recvfrom(utils.BUFFER_SIZE)
            msg = data.decode()
            if msg.startswith(utils.CMD_ANIMATION):
                _, x, y = msg.split(":")
                game_state["flecha_x"] = int(x)
                game_state["flecha_y"] = int(y)
                renderizar()
        except: break

def main():
    global running, game_state
    utils.limpar_tela()
    
    # --- CONEXÃO INICIAL ---
    ip = input("IP do Servidor: ")
    nome = input("Seu Nickname: ")
    
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        tcp.connect((ip, utils.TCP_PORT))
        tcp.send(nome.encode())
    except:
        print("Não foi possível conectar ao servidor."); return

    # --- LOBBY ---
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
                # Fica bloqueado aqui até receber START
                in_lobby = False
        
        elif op == '2':
            tcp.send(utils.CMD_LIST.encode())
            lista = tcp.recv(utils.BUFFER_SIZE).decode()
            print("\n" + lista)
            rid = input("Digite o ID da sala para entrar (ou ENTER para voltar): ")
            if rid:
                tcp.send(f"{utils.CMD_JOIN}:{rid}".encode())
                resp = tcp.recv(utils.BUFFER_SIZE).decode()
                if resp.startswith(utils.CMD_ERROR):
                    print(f"Erro: {resp}")
                    time.sleep(2)
                else:
                    # Se não deu erro, assume que o próximo msg será START
                    # Mas o socket.recv lê bytes, então o START pode estar no buffer já
                    # Vamos tratar isso no loop de jogo
                    in_lobby = False
    
    # --- SETUP UDP ---
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(('0.0.0.0', utils.UDP_PORT))
    threading.Thread(target=udp_listener, args=(udp,), daemon=True).start()

    # --- LOOP DO JOGO ---
    # Espera sinal de START oficial
    while running:
        try:
            msg = tcp.recv(utils.BUFFER_SIZE).decode()
            if not msg: break
            
            if msg.startswith(utils.CMD_START):
                # START:NomeOponente:ID
                _, op_nome, my_id = msg.split(":")
                if my_id == '1':
                    game_state['p1_nome'] = nome
                    game_state['p2_nome'] = op_nome
                else:
                    game_state['p1_nome'] = op_nome
                    game_state['p2_nome'] = nome
                
                print("\nOPONENTE ENCONTRADO! O JOGO VAI COMEÇAR...")
                time.sleep(2)
                renderizar()
                
            elif msg.startswith(utils.CMD_RESULT):
                # RESULT:HP1:HP2:STATUS
                parts = msg.split(":")
                game_state['p1_hp'] = int(parts[1])
                game_state['p2_hp'] = int(parts[2])
                game_state['flecha_x'] = -1 # Reseta flecha
                renderizar()
                
                status = parts[3]
                if status == "WIN":
                    print("\n\n>>> VICTORY! <<<")
                    running = False
                elif status == "LOSE":
                    print("\n\n>>> GAME OVER <<<")
                    running = False
                elif status == "DRAW":
                    print("\n\n>>> EMPATE <<<")
                    running = False
                # Se for NEXT, continua o loop
                
            # SE NÃO É RESULTADO NEM START, É HORA DE JOGAR?
            # A lógica é: depois de receber resultado (ou start), eu jogo.
            
            if running:
                print("\n--- SUA VEZ ---")
                print(f"Escolha alvo/defesa: {utils.PART_HEAD}, {utils.PART_TORSO}, {utils.PART_LEGS}")
                
                valid = False
                while not valid:
                    escolha = input(">> ").upper()
                    if "CAB" in escolha: escolha = utils.PART_HEAD; valid = True
                    elif "TRO" in escolha: escolha = utils.PART_TORSO; valid = True
                    elif "PER" in escolha: escolha = utils.PART_LEGS; valid = True
                
                # Feedback visual local imediato
                if game_state['p1_nome'] == nome: game_state['p1_acao'] = escolha
                else: game_state['p2_acao'] = escolha
                renderizar()
                
                print("Enviando... Aguarde o oponente.")
                tcp.send(f"{utils.CMD_CHOICE}:{escolha}".encode())
                
                # Agora o loop volta pro inicio e espera tcp.recv (o Resultado)
                
        except Exception as e:
            print(e)
            break
            
    tcp.close()
    udp.close()

if __name__ == "__main__":
    main()
