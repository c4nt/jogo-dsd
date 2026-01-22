import os
import sys

# --- CONFIGURAÇÕES DE REDE ---
TCP_PORT = 65432       # Porta para lógica do jogo (Confiável)
UDP_PORT = 65433       # Porta para animação (Rápida)
BUFFER_SIZE = 1024     # Tamanho do pacote

# --- CÓDIGOS DE COMANDO (PROTOCOLOS) ---
# Usaremos prefixos simples para saber do que a mensagem se trata
CMD_LOGIN = "LOGIN"
CMD_LOBBY_LIST = "LIST"
CMD_JOIN = "JOIN"
CMD_GAME_START = "START"
CMD_CHOICE = "CHOICE"   # Ex: CHOICE:ATACANTE:CABECA
CMD_RESULT = "RESULT"   # Resultado do turno
CMD_ANIMATION = "ANIM"  # Pacote UDP com coordenadas
CMD_GAME_OVER = "OVER"

# --- PARTES DO CORPO ---
PART_HEAD = "CABECA"
PART_TORSO = "TRONCO"
PART_LEGS = "PERNAS"

# --- VISUAL (ASCII ART) ---
# Limpar tela (funciona em Windows e Linux/Mac)
def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

# Desenha o título
def mostrar_titulo():
    print("="*60)
    print("      D U E L O   G U I L H E R M E   T E L L      ")
    print("="*60)

# Função para desenhar os dois jogadores lado a lado
def desenhar_arena(p1_nome, p1_vida, p1_acao, p2_nome, p2_vida, p2_acao, flecha_x=-1, flecha_y=-1):
    """
    p1_acao/p2_acao: onde está a arma ou escudo (PART_HEAD, PART_TORSO, PART_LEGS) ou 'IDLE'
    flecha_x/y: Coordenadas da flecha (apenas para animação UDP)
    """
    
    # Base do cenário (10 linhas de altura por 60 de largura)
    cenario = [[' ' for _ in range(60)] for _ in range(15)]
    
    # --- JOGADOR 1 (Esquerda - Atacante/Defensor) ---
    # Cabeça (y=2)
    cenario[2][5] = 'O'
    # Tronco (y=3)
    cenario[3][4] = '/' 
    cenario[3][5] = '|'
    cenario[3][6] = '\\'
    # Pernas (y=4)
    cenario[4][4] = '/'
    cenario[4][6] = '\\'

    # Arma/Escudo P1
    if p1_acao == PART_HEAD:   arma_y = 2
    elif p1_acao == PART_TORSO: arma_y = 3
    else:                       arma_y = 4 # Legs ou Idle
    
    # Desenho simples da balestra ou escudo (P1 olha pra direita >)
    cenario[arma_y][8] = '}'  # Escudo ou arco

    # --- JOGADOR 2 (Direita - Atacante/Defensor) ---
    p2_base_x = 54
    # Cabeça
    cenario[2][p2_base_x] = 'O'
    # Tronco
    cenario[3][p2_base_x-1] = '/' 
    cenario[3][p2_base_x] = '|' 
    cenario[3][p2_base_x+1] = '\\'
    # Pernas
    cenario[4][p2_base_x-1] = '/' 
    cenario[4][p2_base_x+1] = '\\'

    # Arma/Escudo P2 (Olha pra esquerda <)
    if p2_acao == PART_HEAD:   arma_y_p2 = 2
    elif p2_acao == PART_TORSO: arma_y_p2 = 3
    else:                       arma_y_p2 = 4
    
    cenario[arma_y_p2][p2_base_x-3] = '{' 

    # --- FLECHA (Se estiver voando) ---
    if flecha_x > 0 and flecha_y > 0 and flecha_x < 60 and flecha_y < 15:
        cenario[int(flecha_y)][int(flecha_x)] = '-' 
        if int(flecha_x) + 1 < 60: cenario[int(flecha_y)][int(flecha_x)+1] = '>'

    # --- RENDERIZAÇÃO ---
    print("\n")
    print(f" {p1_nome} (HP: {'♥ '*p1_vida})".ljust(30) + f"{p2_nome} (HP: {'♥ '*p2_vida})".rjust(30))
    print("-" * 60)
    for linha in cenario:
        print("".join(linha))
    print("-" * 60)

# Exemplo de teste visual (se rodar este arquivo direto)
if __name__ == "__main__":
    limpar_tela()
    mostrar_titulo()
    desenhar_arena("Heroi", 3, PART_HEAD, "Vilao", 3, PART_LEGS, flecha_x=30, flecha_y=2)
    print("\n[TESTE] Visualizando arena...")
