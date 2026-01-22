import socket
import threading
import sys
import utils
import time

# --- VARIÁVEIS GLOBAIS DE ESTADO ---
# Precisamos delas globais para a thread UDP atualizar o desenho
# enquanto a thread principal espera o input.
game_state = {
    "p1_nome": "Player 1",
    "p2_nome": "Player 2",
    "p1_hp": 3,
    "p2_hp": 3,
    "p1_acao": "IDLE", # Onde está a arma
    "p2_acao": "IDLE",
    "flecha_x": -1,
    "flecha_y": -1
}

running = True

def renderizar():
    """Chama a função de desenho do utils com os dados atuais"""
    utils.limpar_tela()
    utils.mostrar_titulo()
    utils.desenhar_arena(
        game_state["p1_nome"], game_state["p1_hp"], game_state["p1_acao"],
        game_state["p2_nome"], game_state["p2_hp"], game_state["p2_acao"],
        game_state["flecha_x"], game_state["flecha_y"]
    )

def udp_listener(udp_sock):
    """Thread que fica ouvindo apenas dados de animação (Rápido)"""
    global game_state
    while running:
        try:
            data, _ = udp_sock.recvfrom(utils.BUFFER_SIZE)
            msg = data.decode()
            
            if msg.startswith(utils.CMD_ANIMATION):
                # Formato: ANIM:X:Y
                parts = msg.split(":")
                game_state["flecha_x"] = int(parts[1])
                game_state["flecha_y"] = int(parts[2])
                
                # Redesenha a tela instantaneamente para dar fluidez
                renderizar()
                
        except:
            break

def main():
    global running, game_state
    
    # 1. Configuração Inicial
    utils.limpar_tela()
    print("--- CONECTAR AO JOGO ---")
    server_ip = input("Digite o IP do servidor (ex: 127.0.0.1): ")
    player_name = input("Seu Nickname: ")

    # 2. Conexão TCP (Controle)
    try:
        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_sock.connect((server_ip, utils.TCP_PORT))
        
        # Envia login
        tcp_sock.send(player_name.encode())
        print("Conectado! Aguardando oponente...")
    except Exception as e:
        print(f"Erro ao conectar TCP: {e}")
        return

    # 3. Setup UDP (Animação)
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # IMPORTANTE: Bind na porta que o servidor espera mandar dados
    # Se estiver rodando servidor e cliente no MESMO PC, isso vai dar erro de porta em uso.
    # Nesse caso, teste em PCs diferentes ou mude a porta UDP no utils.py para teste.
    try:
        udp_sock.bind(('0.0.0.0', utils.UDP_PORT))
        udp_sock.settimeout(2.0) # Timeout para não travar desligamento
    except:
        print("Erro: Porta UDP ocupada. Se estiver testando local, feche outras instâncias.")
        return

    # Inicia thread de animação
    t_udp = threading.Thread(target=udp_listener, args=(udp_sock,))
    t_udp.daemon = True
    t_udp.start()

    # 4. Loop Principal (Lógica TCP)
    while running:
        try:
            msg = tcp_sock.recv(utils.BUFFER_SIZE).decode()
            
            if not msg:
                break

            # --- PARSING DOS COMANDOS TCP ---
            
            if msg.startswith(utils.CMD_GAME_START):
                # Msg: START:NomeOponente:SeuID(1ou2)
                _, op_name, my_id = msg.split(":")
                game_state["p1_nome"] = player_name if my_id == '1' else op_name
                game_state["p2_nome"] = op_name if my_id == '1' else player_name
                print("JOGO INICIADO!")
                time.sleep(1)

            elif "AGUARDANDO_OPONENTE" in msg:
                print("Esperando alguém entrar na sala...")

            # O servidor pediu uma ação? (Não implementamos request explicito, 
            # assumimos que se não é fim de jogo, é turno novo)
            # Vamos identificar se é hora de jogar pelo fluxo.
            # Como simplificação, vamos assumir loop de input local:
            
            if "WIN" in msg or "LOSE" in msg:
                # Recebemos resultado final
                parts = msg.split(":") 
                # CMD:HP1:HP2:STATUS:ACHIEVEMENT
                # Ex: RESULT:2:3:LOSE:
                
                # Atualiza HP final
                game_state["p1_hp"] = int(parts[1])
                game_state["p2_hp"] = int(parts[2])
                renderizar()
                
                print("\n\n" + "="*30)
                if "WIN" in parts[3]:
                    print("       V I T Ó R I A !       ")
                    if "PERFECT_AIM" in parts[4]:
                        print(" >> CONQUISTA DESBLOQUEADA: MIRA PERFEITA <<")
                else:
                    print("       D E R R O T A ...     ")
                print("="*30)
                running = False
                break
            
            elif msg.startswith(utils.CMD_RESULT):
                # Resultado parcial de um turno
                # O UDP já deve ter feito a animação da flecha antes dessa msg chegar/processar
                # Resetamos a flecha
                game_state["flecha_x"] = -1
                parts = msg.split(":")
                game_state["p1_hp"] = int(parts[1])
                game_state["p2_hp"] = int(parts[2])
                renderizar()
                # Segue para input abaixo...

            # --- INPUT DO JOGADOR ---
            # Se o jogo continua, pedimos input
            if running:
                print("\nSua vez! Onde mirar/defender?")
                print(f"Opcoes: {utils.PART_HEAD}, {utils.PART_TORSO}, {utils.PART_LEGS}")
                
                valido = False
                escolha = ""
                while not valido:
                    opcao = input("Digite sua escolha: ").upper()
                    if "CAB" in opcao: escolha = utils.PART_HEAD; valido = True
                    elif "TRO" in opcao: escolha = utils.PART_TORSO; valido = True
                    elif "PER" in opcao: escolha = utils.PART_LEGS; valido = True
                    else: print("Opção inválida.")
                
                # Atualiza visual local da arma (opcional, só para feedback)
                if game_state["p1_nome"] == player_name: game_state["p1_acao"] = escolha
                else: game_state["p2_acao"] = escolha
                
                renderizar()
                print("Aguardando oponente...")
                
                # Envia TCP
                tcp_sock.send(f"{utils.CMD_CHOICE}:{escolha}".encode())
                
                # Agora ficamos presos no tcp_sock.recv lá no topo do loop
                # esperando o resultado. Enquanto isso, o UDP vai desenhar a flecha.

        except OSError:
            break
        except Exception as e:
            print(f"Erro no loop principal: {e}")
            break

    tcp_sock.close()
    udp_sock.close()
    print("Jogo encerrado.")

if __name__ == "__main__":
    main()
