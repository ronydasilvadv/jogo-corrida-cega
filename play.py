# -*- coding: utf-8 -*-
import pygame
import random
import time
import numpy as np
import pyttsx3
import pyperclip
from datetime import datetime
import threading
import socket
import os
import sys

# Variáveis Globais de Controle
jogo_encerrar = False

# Variáveis Globais de Debounce
last_home_press_time = 0
last_v_press_time = 0
debounce_interval = 0.3

# Configuração de Voz SAPI, pyttsx3
voz_sapi = None
voz_sapi_ocupada = False # Variável global controlada pelos callbacks
voz_sapi_lock = threading.Lock()
voz_sapi_terminou_evento = threading.Event()

# NOVA THREAD PARA EXECUTAR O SAPI
sapi_thread = None

def run_sapi_engine():
    """Função para ser executada na thread persistente do SAPI."""
    global voz_sapi
    if voz_sapi:
        try:
            # print("DEBUG: [SAPI ENGINE THREAD] Iniciando runAndWait em thread dedicada.")
            voz_sapi.runAndWait() # Loop principal do SAPI
            # print("DEBUG: [SAPI ENGINE THREAD] runAndWait terminou.")
        except Exception as e:
            # print(f"ERRO: [SAPI ENGINE THREAD] Exceção na thread do SAPI: {e}")
            global jogo_encerrar
            jogo_encerrar = True # Se o motor falha, encerra o jogo

def inicializar_voz_sapi():
    """Inicializa o pyttsx3 (SAPI) de forma segura e inicia sua thread."""
    global voz_sapi, jogo_encerrar, sapi_thread, voz_sapi_ocupada

    try:
        voz_sapi = pyttsx3.init(driverName='sapi5', debug=False)
        voz_sapi.setProperty('rate', 225)
        voz_sapi.connect('finished-utterance', on_speech_end)

        # Inicia a thread do motor do SAPI UMA VEZ
        sapi_thread = threading.Thread(target=run_sapi_engine, daemon=True)
        sapi_thread.start()
        # print("INFO: Thread para runAndWait do pyttsx3 iniciada.")

        # Teste rápido do SAPI após inicialização da thread
        try:
            # print("DEBUG: [SAPI TESTE] Tentando uma fala de teste após inicialização da thread do SAPI...")
            voz_sapi.say("Carregando...")

            # Aguarda o evento de término da fala de teste ou um timeout
            # test_start = time.time() # Variável não usada
            voz_sapi_terminou_evento.wait(timeout=2.0) # Espera até 2 segundos para a fala de teste terminar

            if voz_sapi_ocupada: # Se ainda estiver ocupado após o wait, algo deu errado
                # print("AVISO: [SAPI TESTE] A fala de teste inicial não foi concluída. SAPI pode estar com problemas.")
                voz_sapi.stop()
                voz_sapi_ocupada = False
                voz_sapi_terminou_evento.set()
            # else:
                # print("DEBUG: [SAPI TESTE] Fala de teste inicial aparentemente bem-sucedida.")

        except Exception as test_e:
            # print(f"AVISO: [SAPI TESTE] Falha na fala de teste inicial do SAPI: {test_e}. SAPI pode não funcionar.")
            pass # Não mostra erros de teste para o usuário final

        # print("INFO: pyttsx3 (SAPI) inicializado com sucesso.")

    except Exception as e:
        # print(f"ERRO CRÍTICO: Falha ao inicializar pyttsx3 (SAPI): {e}. O jogo não pode continuar sem voz.")
        voz_sapi = None
        jogo_encerrar = True

def on_speech_end(name, completed):
    """Callback chamado pelo pyttsx3 quando uma fala é concluída."""
    global voz_sapi_ocupada
    with voz_sapi_lock:
        voz_sapi_ocupada = False
        voz_sapi_terminou_evento.set()
        # print(f"DEBUG: [FALA CALLBACK] Fala '{name}' concluída. voz_sapi_ocupada resetada para False via callback.")


# Funções de Fala Universais

def falar_universal(texto, prioridade=False):
    """
    Função principal para todas as falas do jogo.
    Utiliza exclusivamente o SAPI (pyttsx3) de forma assíncrona e não bloqueante.
    Se 'prioridade' for True, tentará interromper a fala atual para falar este texto.
    """
    global voz_sapi_ocupada
    if voz_sapi is None:
        # print(f"AVISO: Tentativa de falar '{texto}', mas SAPI não está inicializado.")
        return

    with voz_sapi_lock:
        if voz_sapi_ocupada:
            if prioridade:
                # print(f"DEBUG: [FALA] Prioridade ativada. Parando fala atual para '{texto}'.")
                try:
                    voz_sapi.stop()
                    time.sleep(0.05)
                except RuntimeError as e:
                    # print(f"AVISO: [FALA] RuntimeError ao tentar parar SAPI para prioridade: {e}")
                    pass
                finally:
                    voz_sapi_ocupada = False
                    voz_sapi_terminou_evento.set()
            # else:
                # print(f"DEBUG: [FALA] SAPI já ocupado. Não pode falar '{texto}' agora.")
                return

        if not voz_sapi_ocupada:
            voz_sapi_ocupada = True
            voz_sapi_terminou_evento.clear()
            # print(f"DEBUG: [FALA] Solicitando fala: '{texto}' (voz_sapi_ocupada=True)")

            voz_sapi.say(texto)


def parar_fala_voz():
    """
    Interrompe a fala atual do SAPI de forma imediata e reseta a flag de ocupação.
    Também limpa o buffer de eventos do Pygame.
    """
    global voz_sapi_ocupada
    if voz_sapi is not None:
        with voz_sapi_lock:
            if voz_sapi_ocupada:
                try:
                    voz_sapi.stop()
                    # print("DEBUG: [FALA] SAPI stop() chamado.")
                    time.sleep(0.05)
                except RuntimeError as e:
                    # print(f"AVISO: [FALA] RuntimeError ao tentar parar SAPI: {e}")
                    pass
                finally:
                    voz_sapi_ocupada = False
                    voz_sapi_terminou_evento.set()
                    # print("DEBUG: [FALA] voz_sapi_ocupada resetada para False na parada.")
    pygame.event.clear()

# Inicialização do Pygame
try:
    pygame.init()
    # print("INFO: Pygame inicializado.")
except Exception as e:
    # print(f"ERRO CRÍTICO: Falha ao inicializar Pygame: {e}. O jogo não pode ser executado.")
    sys.exit(1)

try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    # print("INFO: Pygame Mixer inicializado.")
except Exception as e:
    # print(f"ERRO CRÍTICO: Falha ao inicializar Pygame Mixer: {e}. Verifique sua placa de som ou drivers.")
    sys.exit(1)

# Tela do Pygame (Aumentada para maior compatibilidade)
tela = pygame.display.set_mode((100, 100))
pygame.display.set_caption("Corrida Cega")
# print("INFO: Janela do Pygame criada com tamanho (100, 100).")


# Caminhos dos Sons
sons_paths = {
    "instrucoes": "sons/instrucoes.mp3",
    "inicio": "sons/inicio_jogo.mp3",
    "musica": "sons/musica_fundo.mp3",
    "colisao": "sons/colisao.wav",
    "desviou": "sons/desviou.wav",
    "fim": "sons/fim_de_jogo.mp3",
    "centro": "sons/obstaculo_centro.wav",
    "cima": "sons/obstaculo_cima.wav",
    "caixa": "sons/bonus_caixa.wav",
    "vida": "sons/vida.wav",
    "obstaculos_varios": [
        "sons/obstaculo_1.wav",
        "sons/obstaculo_2.wav",
        "sons/obstaculo_3.wav",
        "sons/obstaculo_4.wav"
    ],
    "teste_autofalante_base": "sons/obstaculo_1.wav"
}

# Carregar Sons
loaded_sounds = {}
for key, value in sons_paths.items():
    if isinstance(value, list):
        loaded_sounds[key] = []
        for f_path in value:
            try:
                full_path = os.path.join(os.getcwd(), f_path)
                loaded_sounds[key].append(pygame.mixer.Sound(full_path))
                # print(f"INFO: Som '{f_path}' carregado com sucesso.")
            except pygame.error as e:
                # print(f"ERRO: Falha ao carregar som '{f_path}' para '{key}': {e}. Este som pode não tocar.")
                loaded_sounds[key].append(None)
            except FileNotFoundError:
                # print(f"ERRO: Arquivo de som '{f_path}' não encontrado para '{key}'. Este som não tocará.")
                loaded_sounds[key].append(None)
    elif key not in ["musica", "instrucoes", "inicio", "fim"]:
        try:
            full_path = os.path.join(os.getcwd(), value)
            loaded_sounds[key] = pygame.mixer.Sound(full_path)
            # print(f"INFO: Som '{value}' carregado com sucesso.")
        except pygame.error as e:
            # print(f"ERRO: Falha ao carregar som '{value}' para '{key}': {e}. Este som não tocará.")
            loaded_sounds[key] = None
        except FileNotFoundError:
            # print(f"ERRO: Arquivo de som '{value}' não encontrado para '{key}'. Este som não tocará.")
            loaded_sounds[key] = None


# Funções Auxiliares de Áudio e Voz

def falar_pontuacao_total(pontos):
    falar_universal(f"Sua pontuação é de {pontos} pontos.", prioridade=True)

def falar_nivel_progresso(pontos_atuais):
    nivel = (pontos_atuais // 10) + 1
    falar_universal(f"Nível {nivel}", prioridade=True)

def falar_vidas_restantes(colisoes_restantes):
    falar_universal(f"Você tem {colisoes_restantes} vidas restantes." if colisoes_restantes != 1 else "Você tem 1 vida restante.", prioridade=True)

def tocar_som(nome_som):
    """Toca um som curto (Sound object) de forma não bloqueante."""
    try:
        if nome_som in loaded_sounds and loaded_sounds[nome_som] is not None:
            if isinstance(loaded_sounds[nome_som], list):
                playable_sounds = [s for s in loaded_sounds[nome_som] if s is not None]
                if playable_sounds:
                    random.choice(playable_sounds).play()
                # else:
                    # print(f"AVISO: Nenhuma versão válida do som '{nome_som}' para tocar.")
            else:
                loaded_sounds[nome_som].play()
        # else:
            # print(f"AVISO: Som '{nome_som}' não encontrado ou não carregado para tocar.")
    except Exception as e:
        # print(f"ERRO ao tocar som '{nome_som}': {e}")
        pass # Não exibe erro para o usuário final

def tocar_e_esperar(som_nome):
    """
    Toca um som (geralmente MP3 longo) usando pygame.mixer.music e espera sua duração.
    Bloqueante - usado para introduções, instruções e fim de jogo.
    """
    global jogo_encerrar
    try:
        if som_nome in sons_paths:
            full_path = os.path.join(os.getcwd(), sons_paths[som_nome])
            pygame.mixer.music.load(full_path)
            pygame.mixer.music.play()
            start_time = time.time()
            max_wait = 10
            while pygame.mixer.music.get_busy() and (time.time() - start_time < max_wait):
                for event in get_all_pygame_events(): # Permite sair durante a reprodução
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        jogo_encerrar = True
                        pygame.mixer.music.stop()
                        return
                pygame.time.Clock().tick(30)
            if pygame.mixer.music.get_busy():
                # print(f"AVISO: Som '{som_nome}' não terminou dentro do tempo limite. Forçando parada.")
                pygame.mixer.music.stop()
        # else:
            # print(f"AVISO: Som '{som_nome}' não encontrado em sons_paths para tocar e esperar.")
    except pygame.error as e:
        # print(f"ERRO: Falha ao carregar ou tocar música '{som_nome}': {e}. Verifique o arquivo.")
        pass # Não exibe erro para o usuário final
    except FileNotFoundError:
        # print(f"ERRO: Arquivo de som '{sons_paths[som_nome]}' não encontrado. Música não tocará.")
        pass # Não exibe erro para o usuário final
    except Exception as e:
        # print(f"ERRO inesperado ao tocar e esperar som '{som_nome}': {e}")
        pass # Não exibe erro para o usuário final


def tocar_som_direcional(nome_evento, direcao, sound_obj=None):
    """
    Toca um som com efeito de pan direcional (estéreo).
    Direções: "esquerda", "direita", "centro".
    Pode receber um sound_obj diretamente para teste de autofalantes.
    """
    try:
        original_sound = sound_obj
        if original_sound is None:
            if nome_evento in ["esquerda", "direita"]:
                if "obstaculos_varios" in loaded_sounds and loaded_sounds["obstaculos_varios"]:
                    playable_sounds = [s for s in loaded_sounds["obstaculos_varios"] if s is not None]
                    if playable_sounds:
                        original_sound = random.choice(playable_sounds)
            elif nome_evento in loaded_sounds and loaded_sounds[nome_evento] is not None:
                original_sound = loaded_sounds[nome_evento]

        if original_sound is None:
            # print(f"AVISO: Som direcional para '{nome_evento}' não carregado ou não encontrado.")
            return

        som_array = pygame.sndarray.array(original_sound).astype(np.float32)

        if som_array.ndim == 1:
            som_array = np.stack((som_array, som_array), axis=-1)

        pan_reduction_factor = 0.1
        if direcao == "esquerda":
            som_array[:, 1] *= pan_reduction_factor
        elif direcao == "direita":
            som_array[:, 0] *= pan_reduction_factor

        som_modificado = pygame.sndarray.make_sound(som_array.astype(np.int16))
        som_modificado.play()
    except Exception as e:
        # print(f"ERRO ao tocar som direcional '{nome_evento}': {e}")
        pass # Não exibe erro para o usuário final

def iniciar_musica_fundo():
    """Inicia a música de fundo em loop."""
    try:
        full_path = os.path.join(os.getcwd(), sons_paths["musica"])
        pygame.mixer.music.load(full_path)
        pygame.mixer.music.set_volume(0.7)
        pygame.mixer.music.play(-1)
        # print("INFO: Música de fundo iniciada.")
    except pygame.error as e:
        # print(f"ERRO: Falha ao carregar ou iniciar música de fundo: {e}. Verifique o arquivo 'musica_fundo.mp3'.")
        pass # Não exibe erro para o usuário final
    except FileNotFoundError:
        # print(f"ERRO: Arquivo de música '{sons_paths['musica']}' não encontrado. Música de fundo não tocará.")
        pass # Não exibe erro para o usuário final
    except Exception as e:
        # print(f"ERRO inesperado ao iniciar música de fundo: {e}")
        pass # Não exibe erro para o usuário final

# Função UNIFICADA para Coletar Eventos Pygame
def get_all_pygame_events():
    """Coleta e retorna todos os eventos pendentes do Pygame. Limpa a fila de eventos."""
    global jogo_encerrar
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            jogo_encerrar = True
    return events


# Função Auxiliar para Processamento de Eventos de Menu com Controle SAPI
def processar_eventos_menu_com_sapi_check():
    """
    Processa eventos Pygame em loops de menu, garantindo interrupção de fala
    e retorno de input válido. Monitora o estado do SAPI para evitar "puladas".
    Retorna a tecla pressionada ou None se nenhum input relevante.
    """
    global jogo_encerrar
    for evento in get_all_pygame_events(): # Usa a função unificada
        if jogo_encerrar: # Verifica se um evento QUIT ou ESC foi detectado na coleta unificada
            return 'QUIT'
        elif evento.type == pygame.KEYDOWN:
            parar_fala_voz()
            return evento.unicode
    return None

def falar_opcoes_segmentado(opcoes_list):
    """
    Fala uma lista de frases segmentadamente, permitindo interrupção
    e garantindo que cada frase seja falada antes da próxima.
    Retorna a tecla pressionada que interrompeu a fala, ou None.
    """
    global voz_sapi_ocupada, jogo_encerrar
    for frase in opcoes_list:
        if jogo_encerrar:
            return 'QUIT'

        # Espera ativa para a fala anterior terminar e o SAPI estar livre
        wait_start_time = time.time()
        # print(f"DEBUG: [SAPI_SEGMENTADO] Aguardando SAPI ficar livre para '{frase}'. Ocupado: {voz_sapi_ocupada}")

        # Espera pelo evento ou timeout, permitindo input
        while voz_sapi_ocupada and not voz_sapi_terminou_evento.is_set() and (time.time() - wait_start_time < 10):
            input_during_wait = processar_eventos_menu_com_sapi_check()
            if input_during_wait is not None:
                return input_during_wait
            if jogo_encerrar: return 'QUIT'
            pygame.time.Clock().tick(60)

        # Se a flag ainda está True e o evento não foi setado após o timeout, algo está errado
        if voz_sapi_ocupada and not voz_sapi_terminou_evento.is_set():
            # print(f"AVISO: [SAPI_SEGMENTADO] Timeout ({10}s) esperando SAPI liberar. Forçando parada para '{frase}'.")
            parar_fala_voz()

        if jogo_encerrar: return 'QUIT'

        # Tenta falar a nova frase
        falar_universal(frase)

        # Pequena pausa ativa para SAPI iniciar a fala e checar input
        # print(f"DEBUG: [SAPI_SEGMENTADO] Falando: '{frase}'. Aguardando término ou input.")
        current_segment_start = time.time()
        # Tempo de espera aumentado para 8 segundos para frases mais longas
        while not voz_sapi_terminou_evento.is_set() and (time.time() - current_segment_start < 8):
            input_event = processar_eventos_menu_com_sapi_check()
            if input_event is not None:
                return input_event
            if jogo_encerrar: return 'QUIT'
            pygame.time.Clock().tick(60)

        voz_sapi_terminou_evento.clear()
        # print(f"DEBUG: [SAPI_SEGMENTADO] Segmento para '{frase}' finalizado (ou interrompido/timeout).")

    # Se todas as frases foram faladas sem interrupção, aguarda um input final
    while True:
        input_final = processar_eventos_menu_com_sapi_check()
        if input_final is not None:
            return input_final
        if jogo_encerrar:
            return 'QUIT'
        pygame.time.Clock().tick(60)

# Submenu de Teste de Sons
def exibir_submenu_sons():
    """Exibe e gerencia o submenu para teste de sons."""

    opcoes_sons = [
        "Menu de sons.",
        "1. Caixa com Vida Extra.",
        "2. Pegou vida extra.",
        "3. colidiu com obstáculo.",
        "4. obstáculo acima.",
        "5. obstáculo no centro.",
        "6. esquivou com sucesso.",
        "Pressione zero para voltar ao menu principal."
    ]

    selecionando_som = True
    while selecionando_som:
        input_tecla = falar_opcoes_segmentado(opcoes_sons)

        if input_tecla == 'QUIT':
            selecionando_som = False
            break

        # CORREÇÃO AQUI: Tratar '0' como saída do submenu
        if input_tecla == '0':
            falar_universal("Você está no menu principal.")
            selecionando_som = False
            parar_fala_voz() # Garantir que a fala pare
            time.sleep(0.5) # Pequena pausa para a fala terminar
            continue # Continua o loop externo, mas a flag `selecionando_som` já é False

        try:
            opcao_digitada = int(input_tecla) if input_tecla and isinstance(input_tecla, str) and input_tecla.isdigit() else -1
        except (ValueError, TypeError):
            opcao_digitada = -1

        parar_fala_voz()

        if opcao_digitada == 1:
            falar_universal("Caixa com vida extra.")
            tocar_som("caixa") # Usar tocar_som para ser não bloqueante aqui
        elif opcao_digitada == 2:
            falar_universal("Pegou vida extra.")
            tocar_som("vida") # Usar tocar_som para ser não bloqueante aqui
        elif opcao_digitada == 3:
            falar_universal("Colidiu com obstáculo.")
            tocar_som("colisao") # Usar tocar_som para ser não bloqueante aqui
        elif opcao_digitada == 4:
            falar_universal("Obstáculo acima.")
            tocar_som("cima") # Usar tocar_som para ser não bloqueante aqui
        elif opcao_digitada == 5:
            falar_universal("Obstáculo no centro.")
            tocar_som("centro") # Usar tocar_som para ser não bloqueante aqui
        elif opcao_digitada == 6:
            falar_universal("Esquivou com sucesso.")
            tocar_som("desviou") # Usar tocar_som para ser não bloqueante aqui
        else: # Já tratamos o '0' acima, então qualquer outra coisa aqui é inválida
            falar_universal("Opção inválida, digite um número de 1 a 6, ou 0 para voltar ao menu.")

        if selecionando_som: # Só pausa se ainda estiver no submenu
            start_response_pause = time.time()
            while time.time() - start_response_pause < 1.0:
                input_check = processar_eventos_menu_com_sapi_check()
                if input_check == 'QUIT':
                    selecionando_som = False
                    break
                pygame.time.Clock().tick(60)


# Menu de Teste de Autofalantes
def exibir_teste_autofalantes():
    """Toca sons sequencialmente nos autofalantes esquerdo, centro e direito para calibração."""
    global jogo_encerrar

    falar_universal("Testando autofalantes: Tecle qualquer coisa para voltar ao menu.")

    sound_for_test = None
    try:
        if "teste_autofalante_base" in loaded_sounds and loaded_sounds["teste_autofalante_base"] is not None:
                sound_for_test = loaded_sounds["teste_autofalante_base"]
        elif "obstaculos_varios" in loaded_sounds and loaded_sounds["obstaculos_varios"]:
            playable_sounds = [s for s in loaded_sounds["obstaculos_varios"] if s is not None]
            if playable_sounds:
                sound_for_test = playable_sounds[0]
    except IndexError:
        # print("AVISO: Nenhum som disponível para o teste de autofalantes.")
        falar_universal("Não foi possível encontrar um som para testar os autofalantes.")
        time.sleep(1.0)
        return

    if sound_for_test is None:
        falar_universal("Não foi possível encontrar um som para testar os autofalantes.")
        time.sleep(1.0)
        return

    testando = True
    while testando and not jogo_encerrar:
        falar_universal("Esquerda.")
        tocar_som_direcional("teste_autofalante_base", "esquerda", sound_obj=sound_for_test)

        segment_duration = 1.5
        segment_start_time = time.time()
        while time.time() - segment_start_time < segment_duration:
            input_test = processar_eventos_menu_com_sapi_check()
            if input_test is not None:
                testando = False
                break
            if jogo_encerrar: break
            pygame.time.Clock().tick(60)
        if not testando or jogo_encerrar: break

        falar_universal("Centro.")
        tocar_som_direcional("teste_autofalante_base", "centro", sound_obj=sound_for_test)

        segment_start_time = time.time()
        while time.time() - segment_start_time < segment_duration:
            input_test = processar_eventos_menu_com_sapi_check()
            if input_test is not None:
                testando = False
                break
            if jogo_encerrar: break
            pygame.time.Clock().tick(60)
        if not testando or jogo_encerrar: break

        falar_universal("Direita.")
        tocar_som_direcional("teste_autofalante_base", "direita", sound_obj=sound_for_test)

        segment_start_time = time.time()
        while time.time() - segment_start_time < segment_duration:
            input_test = processar_eventos_menu_com_sapi_check()
            if input_test is not None:
                testando = False
                break
            if jogo_encerrar: break
            pygame.time.Clock().tick(60)
        if not testando or jogo_encerrar: break

        falar_universal("Repetindo teste, tecle algo para voltar ao menu.")

        waiting_for_exit = True
        wait_start_time = time.time()
        while waiting_for_exit and (time.time() - wait_start_time < 5):
            input_test = processar_eventos_menu_com_sapi_check()
            if input_test is not None:
                testando = False
                waiting_for_exit = False
                break
            if jogo_encerrar:
                testando = False
                break
            pygame.time.Clock().tick(60)

        if not waiting_for_exit:
            break

    falar_universal("Teste terminado.")
    # Pequeno atraso para a fala de finalização do teste terminar antes de voltar ao menu
    voz_sapi_terminou_evento.wait(timeout=2)
    if voz_sapi_ocupada:
        parar_fala_voz()
    time.sleep(0.5)

# --- Loop Principal do Menu ---
def exibir_menu_principal():
    """Exibe e gerencia o menu principal do jogo."""
    nivel_dificuldade_escolhido = 0
    global jogo_encerrar

    menu_opcoes = [
        "Qual sua opção?",
        "1 modo fácil.",
        "2 modo médio.",
        "3 modo difícil.",
        "4 modo impossível.",
        "5 exibe instruções.",
        "6 exibe os sons do jogo.",
        "7 exibe créditos.",
        "8 testa os autofalantes.",
        "9 sai do jogo.",
        "Zero repete as opções."
    ]

    selecionando_menu = True
    while selecionando_menu and not jogo_encerrar:
        input_tecla = falar_opcoes_segmentado(menu_opcoes)

        if input_tecla == 'QUIT': # Captura QUIT do processar_eventos_menu_com_sapi_check
            selecionando_menu = False
            break

        try:
            opcao_digitada = int(input_tecla) if input_tecla and isinstance(input_tecla, str) and input_tecla.isdigit() else -1
        except (ValueError, TypeError):
            opcao_digitada = -1

        parar_fala_voz()

        if 1 <= opcao_digitada <= 4:
            nivel_dificuldade_escolhido = opcao_digitada
            selecionando_menu = False
        elif opcao_digitada == 5:
            falar_universal("Você está passando por um local cheio de obstáculos que impedem a sua corrida. Você cada vez corre mais rápido, mas obstáculos também vem cada vez mais rápido! Seta para a direita desvia dos obstáculos que vem da esquerda. Seta esquerda, dos que vem à direita. Seta para cima, dos que vem no centro. Seta para baixo, dos que vem de cima. Control direito, quebra as caixas bônus que tem vida extra, mas que podem ter inimigos se você não as quebrar. v informa suas vidas atuais. home pausa e retoma a música de fundo. Escape sai do jogo a qualquer momento. Quando suas vidas chegarem a 0, você terá sua pontuação automaticamente copiada para sua área de transferência. É importante conhecer os sons do jogo na opção 6 do menu principal. Os sons que ali não forem exibidos se referem a obstáculos. Boa sorte! Voltando ao menu.")
            voz_sapi_terminou_evento.wait(timeout=60) # Espera mais tempo pelas instruções
            if voz_sapi_ocupada: parar_fala_voz()
        elif opcao_digitada == 6:
            exibir_submenu_sons()
        elif opcao_digitada == 7:
            falar_universal("Jogo desenvolvido por Rony. Agradecimentos especiais a: Deus pela capacitação; Apoiadores pelos exaustivos testes e suporte; Comunidade Pygame por suas ferramentas; Pyttsx3 e Numpy pelas funcionalidades de áudio; E a você, pelo prestígio. Divirta-se! Você está de volta ao menu.")
            voz_sapi_terminou_evento.wait(timeout=20) # Espera mais tempo pelos créditos
            if voz_sapi_ocupada: parar_fala_voz()
        elif opcao_digitada == 8:
            exibir_teste_autofalantes()
        elif opcao_digitada == 9:
            jogo_encerrar = True
            selecionando_menu = False
        elif opcao_digitada == 0:
            falar_universal("Repetindo.")
        else:
            falar_universal("Opção inválida, tente novamente.")

        if selecionando_menu and not jogo_encerrar: # Só pausa se ainda estiver no menu e não for sair
            start_response_pause = time.time()
            while time.time() - start_response_pause < 1.0:
                input_check = processar_eventos_menu_com_sapi_check()
                if input_check == 'QUIT':
                    selecionando_menu = False
                    break
                pygame.time.Clock().tick(60)

    return nivel_dificuldade_escolhido

# Jogo Principal
def iniciar_jogo():
    """Inicia e gerencia o loop principal do jogo."""
    global jogo_encerrar, last_home_press_time, last_v_press_time, debounce_interval

    # Loop de aquecimento do Pygame/SAPI
    # print("DEBUG: Entrando no loop de aquecimento do Pygame/SAPI para estabilização...")
    warmup_start_time = time.time()
    warmup_duration = 2

    while time.time() - warmup_start_time < warmup_duration:
        get_all_pygame_events() # Coleta eventos para detectar QUIT
        if jogo_encerrar:
            # print("DEBUG: QUIT detectado durante o aquecimento. Encerrando o jogo.")
            return
        pygame.time.Clock().tick(60)
        time.sleep(0.01)

    if jogo_encerrar:
        # print("DEBUG: Jogo já marcado para encerrar após aquecimento. Saindo.")
        return

    inicializar_voz_sapi()

    if jogo_encerrar:
        # print("DEBUG: SAPI falhou ao inicializar, ou erro crítico. Encerrando o jogo.")
        return

    falar_universal("Boas vindas ao Corrida Cega")
    # print("DEBUG: [INIT] Aguardando a fala de boas-vindas ('Bem-vindo...') terminar ou timeout.")

    sapi_welcome_start = time.time()
    max_sapi_welcome_wait = 5

    while (time.time() - sapi_welcome_start < max_sapi_welcome_wait) and (not voz_sapi_terminou_evento.is_set()):
        get_all_pygame_events() # Coleta eventos para detectar QUIT
        if jogo_encerrar:
            # print("DEBUG: QUIT detectado durante a espera da fala de boas-vindas. Encerrando o jogo.")
            break
        pygame.time.Clock().tick(60)
        time.sleep(0.01)

    if voz_sapi_ocupada:
        # print("AVISO: [INIT] A fala de boas-vindas pode não ter terminado a tempo. Forçando liberação do SAPI.")
        parar_fala_voz()

    if jogo_encerrar:
        # print("DEBUG: Jogo encerrado pelo usuário ou durante a fala inicial. Saindo.")
        return

    nivel_dificuldade_escolhido = exibir_menu_principal()

    if jogo_encerrar:
        # print("DEBUG: Jogo encerrado pelo usuário no menu principal. Saindo.")
        return

    tocar_e_esperar("inicio")

    falar_universal("Vamos lá!")
    voz_sapi_terminou_evento.wait(timeout=2)
    if voz_sapi_ocupada:
        parar_fala_voz()

    iniciar_musica_fundo()

    colisoes = 0
    max_colisoes = 3
    vidas_extra = 0
    pontos = 0

    # Configurações de Dificuldade (Aceleração Contínua)
    if nivel_dificuldade_escolhido == 1:
        tempo_base_entre_obstaculos = 2.0
        aceleracao_por_ponto = 0.018
        min_tempo_obstaculo = 0.001
        caixa_probabilidade = 15
        dificuldade_texto = "Fácil"
    elif nivel_dificuldade_escolhido == 2:
        tempo_base_entre_obstaculos = 1.5
        aceleracao_por_ponto = 0.025
        min_tempo_obstaculo = 0.001
        caixa_probabilidade = 10
        dificuldade_texto = "Médio"
    elif nivel_dificuldade_escolhido == 3:
        tempo_base_entre_obstaculos = 1.0
        aceleracao_por_ponto = 0.040
        min_tempo_obstaculo = 0.001
        caixa_probabilidade = 5
        dificuldade_texto = "Difícil"
    else: # Nível impossível (4) ou default
        tempo_base_entre_obstaculos = 0.8
        aceleracao_por_ponto = 0.055
        min_tempo_obstaculo = 0.001
        caixa_probabilidade = 2
        dificuldade_texto = "Impossível"

    ultimo_tempo_evento = time.time()
    tempo_entre_obstaculos_atual = tempo_base_entre_obstaculos

    last_score_speak_time = time.time()
    score_speak_interval = 30

    rodando = True
    musica_pausada = False

    # Mapeia as teclas de jogo válidas
    teclas_de_jogo_validas = {
        pygame.K_RIGHT, pygame.K_LEFT, pygame.K_UP, pygame.K_DOWN, pygame.K_RCTRL
    }

    while rodando and not jogo_encerrar:
        events = get_all_pygame_events() # Coleta todos os eventos de uma vez

        # Verifica se algum evento de saída foi detectado na coleta
        if jogo_encerrar:
            break

        for evento in events: # Processa os eventos coletados
            if evento.type == pygame.KEYDOWN:
                current_time = time.time()

                if evento.key == pygame.K_HOME:
                    if current_time - last_home_press_time > debounce_interval:
                        if musica_pausada:
                            pygame.mixer.music.unpause()
                            musica_pausada = False
                        else:
                            pygame.mixer.music.pause()
                            musica_pausada = True
                        last_home_press_time = current_time

                elif evento.key == pygame.K_v:
                    if current_time - last_v_press_time > debounce_interval:
                        colisoes_restantes = (max_colisoes + vidas_extra) - colisoes
                        falar_vidas_restantes(colisoes_restantes)
                        last_v_press_time = current_time

        if not rodando:
            break

        current_time_for_score = time.time()
        if current_time_for_score - last_score_speak_time >= score_speak_interval:
            falar_pontuacao_total(pontos)
            last_score_speak_time = current_time_for_score

        if time.time() - ultimo_tempo_evento >= tempo_entre_obstaculos_atual:
            evento_aleatorio = random.choices(
                ["esquerda", "direita", "centro", "cima", "caixa"],
                weights=[24, 24, 24, 24, caixa_probabilidade],
                k=1
            )[0]

            desviou = False
            # Nova variável para controlar se uma ação já foi tomada para o obstáculo atual
            acao_de_jogo_processada_neste_obstaculo = False 

            tecla_certa = {
                "esquerda": pygame.K_RIGHT,
                "direita": pygame.K_LEFT,
                "centro": pygame.K_UP,
                "cima": pygame.K_DOWN,
                "caixa": pygame.K_RCTRL
            }[evento_aleatorio]

            tocar_som_direcional(evento_aleatorio, evento_aleatorio)
            inicio_tempo_reacao = time.time()

            # Loop para tempo de reação
            while time.time() - inicio_tempo_reacao < 0.7 and not jogo_encerrar:
                reaction_events = get_all_pygame_events() # Coleta eventos específicos para a reação
                if jogo_encerrar: break

                for evento in reaction_events:
                    if evento.type == pygame.KEYDOWN:
                        current_key_time = time.time()

                        if evento.key == pygame.K_HOME:
                            if current_key_time - last_home_press_time > debounce_interval:
                                if musica_pausada:
                                    pygame.mixer.music.unpause()
                                    musica_pausada = False
                                else:
                                    pygame.mixer.music.pause()
                                    musica_pausada = True
                                last_home_press_time = current_key_time
                        elif evento.key == pygame.K_v:
                            if current_key_time - last_v_press_time > debounce_interval:
                                colisoes_restantes = (max_colisoes + vidas_extra) - colisoes
                                falar_vidas_restantes(colisoes_restantes)
                                last_v_press_time = current_key_time
                        
                        # --- Lógica para processar apenas a primeira tecla de jogo ---
                        if not acao_de_jogo_processada_neste_obstaculo:
                            if evento.key in teclas_de_jogo_validas: # Verifica se é uma tecla de jogo
                                if evento.key == tecla_certa:
                                    if evento_aleatorio == "caixa":
                                        vidas_extra += 1
                                        tocar_som("vida")
                                    else:
                                        tocar_som("desviou")
                                    desviou = True
                                else: # Tecla errada pressionada como primeira ação
                                    pass # Não faz nada aqui, a colisão será tratada após o loop de reação
                                
                                acao_de_jogo_processada_neste_obstaculo = True # Marca que uma ação já foi tomada
                                break # Sai do for loop de eventos, processamos a primeira ação válida
                
                if acao_de_jogo_processada_neste_obstaculo or jogo_encerrar:
                    break # Sai do while loop de reação se a ação foi processada ou o jogo encerrou

            # Após o loop de reação, verifica o resultado da ação para o obstáculo
            if not desviou and not jogo_encerrar:
                # Se não desviou E uma ação de jogo não foi processada (nenhuma tecla de jogo pressionada)
                # OU a tecla errada foi pressionada como primeira ação, então conta como colisão.
                # A condição 'not acao_de_jogo_processada_neste_obstaculo' significa que nenhuma tecla de jogo foi pressionada
                # A condição 'desviou' ser False significa que a tecla correta não foi a primeira pressionada (ou nenhuma foi)
                colisoes += 1
                tocar_som("colisao")
            elif desviou and not jogo_encerrar: # Se desviou (ou seja, a tecla certa foi a primeira)
                pontos += 1

                if pontos > 0 and pontos % 10 == 0:
                    falar_nivel_progresso(pontos)

            tempo_entre_obstaculos_atual = max(min_tempo_obstaculo, tempo_base_entre_obstaculos - (pontos * aceleracao_por_ponto))

            ultimo_tempo_evento = time.time()

        if colisoes >= max_colisoes + vidas_extra:
            pygame.mixer.music.stop()
            tocar_e_esperar("fim")

            agora = datetime.now()
            nome_computador = socket.gethostname()

            dia = agora.day
            mes_extenso = agora.strftime('%B').capitalize()
            ano = agora.year
            hora = agora.hour
            minuto = agora.minute

            nivel_final = (pontos // 10) + 1

            resultado = f"Dia {dia} de {mes_extenso} de {ano}, às {hora}:{minuto:02d}, {nome_computador} concluiu o jogo na dificuldade '{dificuldade_texto}' com {pontos} pontos, no nível {nivel_final}."

            pyperclip.copy(resultado)
            # print("Fim de jogo!")
            # print("Resultado copiado para a área de transferência:")
            # print(resultado) # Não imprime para o console/log

            time.sleep(0.5)
            falar_universal(f"Você fez {pontos} pontos no nível {nivel_final}. Resultado copiado para a área de transferência.", prioridade=True)

            timeout_start_sapi_end = time.time()
            max_sapi_wait_at_end = 7
            # Garante que o evento de término da fala final é setado
            voz_sapi_terminou_evento.wait(timeout=max_sapi_wait_at_end)

            if voz_sapi_ocupada:
                # print("AVISO: [FIM] Fala final não terminou a tempo. Forçando parada do SAPI para encerrar o jogo.")
                parar_fala_voz()

            rodando = False
            jogo_encerrar = True
            break

        pygame.display.flip() # Garante que Pygame atualiza a tela (mesmo que seja 100x100 preta)
        pygame.time.Clock().tick(60)

# Ponto de Entrada Principal
if __name__ == "__main__":
    try:
        iniciar_jogo()
    finally:
        if voz_sapi is not None:
            try:
                # print("INFO: Tentando finalizar voz SAPI...")
                parar_fala_voz()
                time.sleep(0.1)
                # Desconecta o COM object para liberar recursos do sistema
                if hasattr(voz_sapi, 'engine') and hasattr(voz_sapi.engine.proxy) and hasattr(voz_sapi.engine.proxy, 'disconnect'):
                    voz_sapi.engine.proxy.disconnect()

                voz_sapi.stop() # Chamado novamente para garantir a parada do runAndWait na thread
                voz_sapi = None
                # print("INFO: Voz SAPI finalizada com sucesso.")
            except Exception as e:
                # print(f"AVISO: Erro ao tentar finalizar voz SAPI no encerramento: {e}")
                pass # Não exibe erro para o usuário final

        if pygame.get_init():
            pygame.quit()
            # print("INFO: Pygame finalizado.")

        # Não há mais logs para fechar ou restaurar os streams originais.
        # Os prints foram comentados/removidos, e a classe DualOutput foi removida.

        # print("INFO: Programa encerrado.") # Este print final não será visível com --noconsole

        if jogo_encerrar:
            sys.exit(0)
        else:
            sys.exit(1)