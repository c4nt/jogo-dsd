import os

# --- CONFIGURAÇÕES DE REDE ---
TCP_PORT = 65432
UDP_PORT = 65433
BUFFER_SIZE = 1024

# --- COMANDOS DO PROTOCOLO ---
CMD_LOGIN = "LOGIN"
CMD_CREATE = "CREATE"     # Criar sala
CMD_LIST = "LIST"         # Pedir lista de salas
CMD_JOIN = "JOIN"         # Entrar em sala (JOIN:ID)
CMD_WAIT = "WAIT"         # Resposta: Aguarde oponente
CMD_START = "START"       # Resposta: Jogo começou (START:NomeOponente:SeuID)
CMD_CHOICE = "CHOICE"     # Jogada (CHOICE:CABECA)
CMD_RESULT = "RESULT"     # Resultado do turno
CMD_ANIMATION = "ANIM"    # UDP: Animação
CMD_ERROR = "ERROR"       # Erro (sala cheia, etc)

# --- PARTES DO CORPO ---
PART_HEAD = "CABECA"
PART_TORSO = "TRONCO"
PART_LEGS = "PERNAS"

# --- VISUAL ---
def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def mostrar_titulo():
    print("="*60)
    print("      D U E L O   G U I L H E R M E   T E L L      ")
    print("="*60)

def desenhar_arena(p1_nome, p1_vida, p1_acao, p2_nome, p2_vida, p2_acao, flecha_x=-1, flecha_y=-1):
    # (Mesmo código visual de antes, mantido para economizar espaço na resposta)
    # Copie a função desenhar_arena da resposta anterior ou use esta versão simplificada:
    
    cenario = [[' ' for _ in range(60)] for _ in range(15)]
    
    # Boneco 1 (Esquerda)
    cenario[2][5] = 'O'; cenario[3][5] = '|'; cenario[4][4] = '/'; cenario[4][6] = '\\'
    cenario[3][4] = '/' if p1_acao != "IDLE" else ' '
    cenario[3][6] = '\\'
    
    # Arma P1
    ay = 2 if p1_acao == PART_HEAD else 3 if p1_acao == PART_TORSO else 4
    cenario[ay][8] = '}'

    # Boneco 2 (Direita)
    bx = 54
    cenario[2][bx] = 'O'; cenario[3][bx] = '|'; cenario[4][bx-1] = '/'; cenario[4][bx+1] = '\\'
    cenario[3][bx-1] = '/'
    cenario[3][bx+1] = '\\' if p2_acao != "IDLE" else ' '

    # Arma P2
    by = 2 if p2_acao == PART_HEAD else 3 if p2_acao == PART_TORSO else 4
    cenario[by][bx-3] = '{'

    # Flecha
    if 0 < flecha_x < 59:
        # Se a flecha estiver na metade ESQUERDA da tela, assume que está indo pra direita (>)
        # Se estiver na metade DIREITA e voltando, poderia ser <
        # Mas o jeito mais fácil sem mudar o protocolo é verificar a origem lógica:
        
        # Vamos desenhar baseado na posição para simplificar:
        char_ponta = '>'
        char_corpo = '-'
        
        # Se você quiser ser perfeccionista, teríamos que enviar a direção pelo UDP.
        # Mas um truque visual é: Se for turno do P2, a flecha é '<'.
        # Como o utils não sabe de quem é o turno, vamos usar um caractere neutro ou manter assim.
        
        # Sugestão de visual neutro (uma "bola de fogo" ou pedra):
        # cenario[int(flecha_y)][int(flecha_x)] = '*' 
        
        # OU mantemos a flecha > por enquanto para não complicar.
        # Se quiser inverter:
        # cenario[int(flecha_y)][int(flecha_x)] = '-'
        # cenario[int(flecha_y)][int(flecha_x)+1] = '>' 
        
        # Para funcionar nos dois sentidos sem bugar:
        try:
            cenario[int(flecha_y)][int(flecha_x)] = '*' # Projétil neutro fica bom nos dois sentidos
        except:
            pass
