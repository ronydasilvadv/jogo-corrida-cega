# -*- coding: utf-8 -*-
import pygame
import random
import time
import numpy as np
import pyperclip
from datetime import datetime
import threading
import socket
import os
import sys
import wx

# Variáveis Globais de Controle
jogo_encerrar = False

# Variáveis Globais de Debounce
last_home_press_time = 0
last_v_press_time = 0
debounce_interval = 0.3

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

# Funções Auxiliares de Áudio

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

# Submenu de Teste de Sons usando dialogs simples
def exibir_submenu_sons():
    """Exibe o submenu para teste de sons usando dialogs."""
    opcoes = [
        "Caixa com Vida Extra",
        "Pegou vida extra",
        "Colidiu com obstáculo",
        "Obstáculo acima",
        "Obstáculo no centro",
        "Esquivou com sucesso",
        "Voltar ao menu principal"
    ]
    
    while True:
        dlg = wx.SingleChoiceDialog(None, "Escolha um som para testar:", "Menu de Sons", opcoes)
        
        if dlg.ShowModal() == wx.ID_OK:
            selection = dlg.GetSelection()
            
            if selection == 0:
                tocar_som("caixa")
            elif selection == 1:
                tocar_som("vida")
            elif selection == 2:
                tocar_som("colisao")
            elif selection == 3:
                tocar_som("cima")
            elif selection == 4:
                tocar_som("centro")
            elif selection == 5:
                tocar_som("desviou")
            elif selection == 6:
                dlg.Destroy()
                break
        else:
            dlg.Destroy()
            break
        
        dlg.Destroy()

# Menu de Teste de Autofalantes usando dialogs
def exibir_teste_autofalantes():
    """Toca sons sequencialmente nos autofalantes esquerdo, centro e direito para calibração."""
    global jogo_encerrar

    sound_for_test = None
    try:
        if "teste_autofalante_base" in loaded_sounds and loaded_sounds["teste_autofalante_base"] is not None:
                sound_for_test = loaded_sounds["teste_autofalante_base"]
        elif "obstaculos_varios" in loaded_sounds and loaded_sounds["obstaculos_varios"]:
            playable_sounds = [s for s in loaded_sounds["obstaculos_varios"] if s is not None]
            if playable_sounds:
                sound_for_test = playable_sounds[0]
    except IndexError:
        wx.MessageBox("Não foi possível encontrar um som para testar os autofalantes.", "Erro", wx.OK | wx.ICON_ERROR)
        return

    if sound_for_test is None:
        wx.MessageBox("Não foi possível encontrar um som para testar os autofalantes.", "Erro", wx.OK | wx.ICON_ERROR)
        return

    # Testa os autofalantes sequencialmente
    wx.MessageBox("Testando autofalante esquerdo...", "Teste de Autofalantes", wx.OK | wx.ICON_INFORMATION)
    tocar_som_direcional("teste_autofalante_base", "esquerda", sound_obj=sound_for_test)
    time.sleep(1.5)
    
    wx.MessageBox("Testando autofalante centro...", "Teste de Autofalantes", wx.OK | wx.ICON_INFORMATION)
    tocar_som_direcional("teste_autofalante_base", "centro", sound_obj=sound_for_test)
    time.sleep(1.5)
    
    wx.MessageBox("Testando autofalante direito...", "Teste de Autofalantes", wx.OK | wx.ICON_INFORMATION)
    tocar_som_direcional("teste_autofalante_base", "direita", sound_obj=sound_for_test)
    time.sleep(1.5)
    
    wx.MessageBox("Teste de autofalantes concluído.", "Teste de Autofalantes", wx.OK | wx.ICON_INFORMATION)

# Classe do Menu Principal usando wxPython
class MenuPrincipal(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Corrida Cega - Menu Principal", size=(400, 500))
        
        self.nivel_dificuldade_escolhido = 0
        self.selected_index = 0
        
        # Criar painel principal
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Título
        title = wx.StaticText(panel, label="Corrida Cega")
        title_font = wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 20)
        
        # Lista de opções
        self.opcoes = [
            "Modo Fácil",
            "Modo Médio", 
            "Modo Difícil",
            "Modo Impossível",
            "Exibir Instruções",
            "Exibir Sons do Jogo",
            "Exibir Créditos",
            "Testar Autofalantes",
            "Sair do Jogo"
        ]
        
        # ListBox para as opções
        self.list_box = wx.ListBox(panel, choices=self.opcoes, style=wx.LB_SINGLE)
        self.list_box.SetSelection(0)
        sizer.Add(self.list_box, 1, wx.ALL | wx.EXPAND, 10)
        
        # Botão de confirmação
        btn_confirmar = wx.Button(panel, label="Confirmar")
        sizer.Add(btn_confirmar, 0, wx.ALL | wx.CENTER, 10)
        
        # Eventos
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_confirmar)
        btn_confirmar.Bind(wx.EVT_BUTTON, self.on_confirmar)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
        # Eventos de teclado
        self.list_box.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        
        panel.SetSizer(sizer)
        self.Center()
        
    def on_key_down(self, event):
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_RETURN or key_code == wx.WXK_SPACE:
            self.on_confirmar(event)
        else:
            event.Skip()
    
    def on_confirmar(self, event):
        selection = self.list_box.GetSelection()
        
        if 0 <= selection <= 3:  # Modos de dificuldade
            self.nivel_dificuldade_escolhido = selection + 1
            self.Close()
        elif selection == 4:  # Instruções
            instrucoes = ("Você está passando por um local cheio de obstáculos que impedem a sua corrida. "
                         "Você cada vez corre mais rápido, mas obstáculos também vem cada vez mais rápido!\n\n"
                         "Controles:\n"
                         "• Seta DIREITA: desvia dos obstáculos que vem da esquerda\n"
                         "• Seta ESQUERDA: desvia dos que vem à direita\n"
                         "• Seta CIMA: desvia dos que vem no centro\n"
                         "• Seta BAIXO: desvia dos que vem de cima\n"
                         "• CTRL DIREITO: quebra as caixas bônus que tem vida extra\n"
                         "• V: informa suas vidas atuais\n"
                         "• HOME: pausa e retoma a música de fundo\n"
                         "• ESCAPE: sai do jogo a qualquer momento\n\n"
                         "Quando suas vidas chegarem a 0, você terá sua pontuação "
                         "automaticamente copiada para sua área de transferência.\n\n"
                         "É importante conhecer os sons do jogo na opção 'Exibir Sons do Jogo'. "
                         "Boa sorte!")
            wx.MessageBox(instrucoes, "Instruções", wx.OK | wx.ICON_INFORMATION)
        elif selection == 5:  # Sons do jogo
            exibir_submenu_sons()
        elif selection == 6:  # Créditos
            creditos = ("Jogo desenvolvido por Rony.\n\n"
                       "Agradecimentos especiais a:\n"
                       "• Deus pela capacitação\n"
                       "• Apoiadores pelos exaustivos testes e suporte\n"
                       "• Comunidade Pygame por suas ferramentas\n"
                       "• Numpy pelas funcionalidades de áudio\n"
                       "• E a você, pelo prestígio.\n\n"
                       "Divirta-se!")
            wx.MessageBox(creditos, "Créditos", wx.OK | wx.ICON_INFORMATION)
        elif selection == 7:  # Teste autofalantes
            exibir_teste_autofalantes()
        elif selection == 8:  # Sair
            global jogo_encerrar
            jogo_encerrar = True
            self.Close()
    
    def on_close(self, event):
        self.Destroy()

# --- Loop Principal do Menu ---
def exibir_menu_principal():
    """Exibe e gerencia o menu principal do jogo usando wxPython."""
    global jogo_encerrar
    
    app = wx.App()
    frame = MenuPrincipal()
    frame.Show()
    app.MainLoop()
    
    if jogo_encerrar:
        return 0
    
    return frame.nivel_dificuldade_escolhido

# Jogo Principal (mantido intacto)
def iniciar_jogo():
    """Inicia e gerencia o loop principal do jogo."""
    global jogo_encerrar, last_home_press_time, last_v_press_time, debounce_interval

    # Loop de aquecimento do Pygame
    warmup_start_time = time.time()
    warmup_duration = 2

    while time.time() - warmup_start_time < warmup_duration:
        get_all_pygame_events() # Coleta eventos para detectar QUIT
        if jogo_encerrar:
            return
        pygame.time.Clock().tick(60)
        time.sleep(0.01)

    if jogo_encerrar:
        return

    nivel_dificuldade_escolhido = exibir_menu_principal()

    if jogo_encerrar or nivel_dificuldade_escolhido == 0:
        return

    tocar_e_esperar("inicio")
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
                        # Apenas exibe no console, sem fala
                        print(f"Vidas restantes: {colisoes_restantes}")
                        last_v_press_time = current_time

        if not rodando:
            break

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
                                print(f"Vidas restantes: {colisoes_restantes}")
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
                colisoes += 1
                tocar_som("colisao")
            elif desviou and not jogo_encerrar: # Se desviou (ou seja, a tecla certa foi a primeira)
                pontos += 1

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
            print("Fim de jogo!")
            print("Resultado copiado para a área de transferência:")
            print(resultado)

            # Mostra resultado em dialog
            wx.MessageBox(f"Você fez {pontos} pontos no nível {nivel_final}.\nResultado copiado para a área de transferência.", 
                         "Fim de Jogo", wx.OK | wx.ICON_INFORMATION)

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
        if pygame.get_init():
            pygame.quit()

        if jogo_encerrar:
            sys.exit(0)
        else:
            sys.exit(1)