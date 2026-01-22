import os

# --- CONFIGURAÇÕES DE REDE ---
TCP_PORT = 65432
UDP_PORT = 65433
BUFFER_SIZE = 1024

# --- COMANDOS DO PROTOCOLO ---
CMD_LOGIN = "LOGIN"
CMD_CREATE = "CREATE"
CMD_LIST = "LIST"
CMD_JOIN = "JOIN"
CMD_WAIT = "WAIT"
CMD_START = "START"
CMD_CHOICE = "CHOICE"
CMD_RESULT = "RESULT"
CMD_ANIMATION = "ANIM" # Agora será ANIM:X:Y:CHAR
CMD_ERROR = "ERROR"

# --- PARTES DO CORPO ---
PART_HEAD = "CABECA"
PART_TORSO = "TRONCO"
PART_LEGS = "PERNAS"

# --- VISUAL (ASCII ART) ---
def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def mostrar_titulo():
    print("="*60)
    print("      D U E L O   G U I L H E R M E   T E L L      ")
    print("="*60)

def desenhar_arena(p1_nome, p1_vida, p1_acao, p2_nome, p2_vida, p2_acao, flecha_x=-1, flecha_y=-1, flecha_char='>'):
    """
    flecha_char: Define se a flecha aponta pra direita '>' ou esquerda '<'
    """
    
    # Base do cenário (15 linhas x 60 colunas)
    cenario = [[' ' for _ in range(60)] for _ in range(15)]
    
    # --- JOGADOR 1 (Esquerda) ---
    cenario[2][5] = 'O'
    cenario[3][5] = '|'; cenario[3][4] = '/'; cenario[3][6] = '\\'
    cenario[4][4] = '/'; cenario[4][6] = '\\'

    # Arma/Escudo P1
    if p1_acao == PART_HEAD:   arma_y = 2
    elif p1_acao == PART_TORSO: arma_y = 3
    else:                       arma_y = 4
    
    if p1_acao != "IDLE": cenario[arma_y][8] = '}'

    # --- JOGADOR 2 (Direita) ---
    p2_base_x = 54
    cenario[2][p2_base_x] = 'O'
    cenario[3][p2_base_x] = '|'; cenario[3][p2_base_x-1] = '/'; cenario[3][p2_base_x+1] = '\\'
    cenario[4][p2_base_x-1] = '/'; cenario[4][p2_base_x+1] = '\\'

    # Arma/Escudo P2
    if p2_acao == PART_HEAD:   arma_y_p2 = 2
    elif p2_acao == PART_TORSO: arma_y_p2 = 3
    else:                       arma_y_p2 = 4
    
    if p2_acao != "IDLE": cenario[arma_y_p2][p2_base_x-3] = '{' 

    # --- FLECHA DIRECIONAL ---
    if 0 < flecha_x < 59 and 0 < flecha_y < 14:
        fx = int(flecha_x)
        fy = int(flecha_y)
        
        if flecha_char == '>':
            # Desenha -->
            cenario[fy][fx] = '>'
            if fx > 0: cenario[fy][fx-1] = '-'
            # if fx > 1: cenario[fy][fx-2] = '-' # Se quiser cauda mais longa
            
        else: # assume '<'
            # Desenha <--
            cenario[fy][fx] = '<'
            if fx < 59: cenario[fy][fx+1] = '-'
            # if fx < 58: cenario[fy][fx+2] = '-'

    # --- RENDERIZAÇÃO ---
    print("\n")
    print(f" {p1_nome} (HP: {'♥ '*p1_vida})".ljust(30) + f"{p2_nome} (HP: {'♥ '*p2_vida})".rjust(30))
    print("-" * 60)
    for linha in cenario: print("".join(linha))
    print("-" * 60)
