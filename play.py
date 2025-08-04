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
    "menu_principal": "sons/menu_principal.wav",
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
    Prioriza sons específicos mapeados em loaded_sounds[nome_evento].
    """
    try:
        original_sound = sound_obj
        if original_sound is None:
            # Tenta obter um som específico para o nome_evento
            if nome_evento in loaded_sounds and loaded_sounds[nome_evento] is not None:
                original_sound = loaded_sounds[nome_evento]
            else:
                # Fallback para sounds genéricos se o nome_evento não tiver um som específico,
                # embora para "esquerda", "direita", "centro", "cima" agora haja sons específicos.
                if "obstaculos_varios" in loaded_sounds and loaded_sounds["obstaculos_varios"]:
                    playable_sounds = [s for s in loaded_sounds["obstaculos_varios"] if s is not None]
                    if playable_sounds:
                        original_sound = random.choice(playable_sounds)

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

# Menu de Teste de Autofalantes usando dialogs
def exibir_teste_autofalantes():
    """Toca sons sequencialmente nos autofalantes esquerdo, centro e direito, uma única vez."""
    
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

    wx.MessageBox("O teste de autofalantes será executado. Você ouvirá o som primeiro na esquerda, depois no centro e por último na direita. Pressione 'OK' para começar.", "Teste de Autofalantes", wx.OK | wx.ICON_INFORMATION)
    
    # Toca os sons sequencialmente
    tocar_som_direcional("teste_autofalante_base", "esquerda", sound_obj=sound_for_test)
    time.sleep(1.5)
    
    tocar_som_direcional("teste_autofalante_base", "centro", sound_obj=sound_for_test)
    time.sleep(1.5)
    
    tocar_som_direcional("teste_autofalante_base", "direita", sound_obj=sound_for_test)
    time.sleep(1.5)
    
    wx.MessageBox("Teste de autofalantes concluído. Repita se necessário.", "Teste de Autofalantes", wx.OK | wx.ICON_INFORMATION)

# Classe do Submenu de Sons
class SubmenuSons(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Sons do Jogo", size=(400, 300))
        
        self.parent = parent
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.opcoes_sons = {
            "Caixa com Vida Extra": "caixa",
            "Pegou vida extra": "vida",
            "Colidiu com obstáculo": "colisao",
            "Obstáculo acima": "cima",
            "Obstáculo no centro": "centro",
            "Esquivou com sucesso": "desviou",
            "Voltar ao menu principal": "voltar"
        }
        
        self.list_box = wx.ListBox(panel, choices=list(self.opcoes_sons.keys()), style=wx.LB_SINGLE)
        sizer.Add(self.list_box, 1, wx.ALL | wx.EXPAND, 10)
        
        panel.SetSizer(sizer)
        
        self.list_box.Bind(wx.EVT_LISTBOX, self.on_selecionar_som)
        self.list_box.Bind(wx.EVT_LISTBOX_DCLICK, self.on_selecionar_som)
        self.list_box.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_CLOSE, self.on_fechar)
        
        self.CenterOnParent()
        self.list_box.SetSelection(0)
    
    def on_selecionar_som(self, event):
        selection = self.list_box.GetSelection()
        if selection != wx.NOT_FOUND:
            nome_display = self.list_box.GetString(selection)
            if nome_display == "Voltar ao menu principal":
                self.EndModal(wx.ID_CANCEL)
            else:
                nome_som = self.opcoes_sons[nome_display]
                tocar_som(nome_som)

    def on_char_hook(self, event):
        key_code = event.GetKeyCode()
        old_selection = self.list_box.GetSelection()

        if key_code == wx.WXK_RETURN:
            self.on_selecionar_som(event)
        elif key_code == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
        elif key_code in [wx.WXK_LEFT, wx.WXK_RIGHT]:
            return
        
        elif key_code == wx.WXK_UP:
            new_selection = max(0, old_selection - 1)
            self.list_box.SetSelection(new_selection)
            if old_selection != new_selection:
                tocar_som("menu_principal")
        elif key_code == wx.WXK_DOWN:
            new_selection = min(len(self.opcoes_sons) - 1, old_selection + 1)
            self.list_box.SetSelection(new_selection)
            if old_selection != new_selection:
                tocar_som("menu_principal")
        elif key_code == wx.WXK_HOME:
            self.list_box.SetSelection(0)
            if old_selection != 0:
                tocar_som("menu_principal")
        elif key_code == wx.WXK_END:
            end_index = len(self.opcoes_sons) - 1
            self.list_box.SetSelection(end_index)
            if old_selection != end_index:
                tocar_som("menu_principal")
        else:
            event.Skip()
            
    def on_fechar(self, event):
        self.EndModal(wx.ID_CANCEL)


# Classe do Menu Principal usando wxPython
class MenuPrincipal(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Corrida Cega - Menu Principal", size=(400, 500))
        
        self.nivel_dificuldade_escolhido = 0
        
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
        
        # Eventos
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        
        panel.SetSizer(sizer)
        self.Center()
        
    def on_char_hook(self, event):
        key_code = event.GetKeyCode()
        old_selection = self.list_box.GetSelection()

        if key_code == wx.WXK_RETURN:
            self.on_confirmar(event)
        
        elif key_code == wx.WXK_ESCAPE:
            self.on_close(event)
        
        elif key_code in [wx.WXK_LEFT, wx.WXK_RIGHT]:
            return
        
        elif key_code == wx.WXK_UP:
            new_selection = max(0, old_selection - 1)
            self.list_box.SetSelection(new_selection)
            if old_selection != new_selection:
                tocar_som("menu_principal")
        
        elif key_code == wx.WXK_DOWN:
            new_selection = min(len(self.opcoes) - 1, old_selection + 1)
            self.list_box.SetSelection(new_selection)
            if old_selection != new_selection:
                tocar_som("menu_principal")

        elif key_code == wx.WXK_HOME:
            self.list_box.SetSelection(0)
            if old_selection != 0:
                tocar_som("menu_principal")
            
        elif key_code == wx.WXK_END:
            end_index = len(self.opcoes) - 1
            self.list_box.SetSelection(end_index)
            if old_selection != end_index:
                tocar_som("menu_principal")
        
        else:
            event.Skip()
    
    def on_confirmar(self, event):
        selection = self.list_box.GetSelection()
        
        if 0 <= selection <= 3:  # Modos de dificuldade
            self.nivel_dificuldade_escolhido = selection + 1
            self.EndModal(wx.ID_OK)
        elif selection == 4:  # Instruções
            instrucoes = ("Você está passando por um local cheio de obstáculos que impedem a sua corrida. "
                          "Você cada vez corre mais rápido, mas obstáculos também vem cada vez mais rápido!\n\n"
                          "Controles:\n"
                          "• Seta DIREITA: desvia dos obstáculos que vem da esquerda\n"
                          "• Seta ESQUERDA: desvia dos que vem à direita\n"
                          "• Seta CIMA: desvia dos que vem no centro\n"
                          "• Seta BAIXO: desvia dos que vem de cima\n"
                          "• CTRL DIREITO ou ESQUERDO: quebra as caixas bônus que tem vida extra\n"
                          "• V: informa suas vidas atuais\n"
                          "• HOME: pausa e retoma a música de fundo\n"
                          "• ESCAPE: sai do jogo a qualquer momento\n\n"
                          "Quando suas vidas chegarem a 0, você terá sua pontuação "
                          "automaticamente copiada para sua área de transferência.\n\n"
                          "É importante conhecer os sons do jogo na opção 'Exibir Sons do Jogo'. "
                          "Boa sorte!")
            wx.MessageBox(instrucoes, "Instruções", wx.OK | wx.ICON_INFORMATION)
        elif selection == 5:  # Sons do jogo
            submenu_sons = SubmenuSons(self)
            submenu_sons.ShowModal()
            submenu_sons.Destroy()
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
            self.EndModal(wx.ID_CANCEL)
    
    def on_close(self, event):
        global jogo_encerrar
        jogo_encerrar = True
        self.EndModal(wx.ID_CANCEL)

# Classe do novo menu de Jogar Novamente
class DialogJogarNovamente(wx.Dialog):
    def __init__(self, parent, resultado):
        super().__init__(parent, title="Fim de Jogo", size=(400, 300))
        
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        msg_text = wx.StaticText(panel, label=resultado)
        sizer.Add(msg_text, 0, wx.ALL | wx.CENTER, 10)
        
        self.opcoes = ["Sim", "Não"]
        self.list_box = wx.ListBox(panel, choices=self.opcoes, style=wx.LB_SINGLE)
        self.list_box.SetSelection(0)
        sizer.Add(self.list_box, 1, wx.ALL | wx.EXPAND, 10)

        panel.SetSizer(sizer)
        
        self.list_box.Bind(wx.EVT_LISTBOX_DCLICK, self.on_confirmar)
        self.list_box.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_CLOSE, self.on_fechar)
        
        self.CenterOnParent()
    
    def on_char_hook(self, event):
        key_code = event.GetKeyCode()
        old_selection = self.list_box.GetSelection()

        if key_code == wx.WXK_RETURN:
            self.on_confirmar(event)
        
        elif key_code == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_NO) # ESCAPE é Não
        
        elif key_code in [wx.WXK_LEFT, wx.WXK_RIGHT]:
            return
            
        elif key_code == wx.WXK_UP:
            new_selection = max(0, old_selection - 1)
            self.list_box.SetSelection(new_selection)
            if old_selection != new_selection:
                tocar_som("menu_principal")
        elif key_code == wx.WXK_DOWN:
            new_selection = min(len(self.opcoes) - 1, old_selection + 1)
            self.list_box.SetSelection(new_selection)
            if old_selection != new_selection:
                tocar_som("menu_principal")
        elif key_code == wx.WXK_HOME:
            self.list_box.SetSelection(0)
            if old_selection != 0:
                tocar_som("menu_principal")
        elif key_code == wx.WXK_END:
            end_index = len(self.opcoes) - 1
            self.list_box.SetSelection(end_index)
            if old_selection != end_index:
                tocar_som("menu_principal")
        else:
            event.Skip()

    def on_confirmar(self, event):
        selection = self.list_box.GetSelection()
        if selection == 0: # Sim
            self.EndModal(wx.ID_YES)
        else: # Não
            self.EndModal(wx.ID_NO)
            
    def on_fechar(self, event):
        self.EndModal(wx.ID_NO)

# --- Jogo Principal ---
def iniciar_jogo(parent_window, nivel_dificuldade_escolhido):
    """Inicia e gerencia o loop principal do jogo."""
    global jogo_encerrar, last_home_press_time, last_v_press_time, debounce_interval
    
    # Loop de aquecimento do Pygame
    warmup_start_time = time.time()
    warmup_duration = 2
    while time.time() - warmup_start_time < warmup_duration:
        get_all_pygame_events()
        if jogo_encerrar:
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

    rodando = True
    musica_pausada = False
    
    teclas_de_jogo_validas = {
        pygame.K_RIGHT, pygame.K_LEFT, pygame.K_UP, pygame.K_DOWN, pygame.K_RCTRL, pygame.K_LCTRL
    }

    while rodando and not jogo_encerrar:
        events = get_all_pygame_events()
        if jogo_encerrar: break

        for evento in events:
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
            acao_de_jogo_processada_neste_obstaculo = False 

            tecla_certa = {
                "esquerda": pygame.K_RIGHT,
                "direita": pygame.K_LEFT,
                "centro": pygame.K_UP,
                "cima": pygame.K_DOWN,
                "caixa": (pygame.K_RCTRL, pygame.K_LCTRL)
            }[evento_aleatorio]

            if evento_aleatorio != "caixa":
                tocar_som_direcional(evento_aleatorio, evento_aleatorio)
            else:
                tocar_som("caixa")
            
            inicio_tempo_reacao = time.time()

            while time.time() - inicio_tempo_reacao < 0.7 and not jogo_encerrar:
                reaction_events = get_all_pygame_events()
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
                        
                        if not acao_de_jogo_processada_neste_obstaculo:
                            if evento.key in teclas_de_jogo_validas:
                                if isinstance(tecla_certa, tuple):
                                    if evento.key in tecla_certa:
                                        if evento_aleatorio == "caixa":
                                            vidas_extra += 1
                                            tocar_som("vida")
                                        else:
                                            tocar_som("desviou")
                                        desviou = True
                                elif evento.key == tecla_certa:
                                    if evento_aleatorio == "caixa":
                                        vidas_extra += 1
                                        tocar_som("vida")
                                    else:
                                        tocar_som("desviou")
                                    desviou = True
                                
                                acao_de_jogo_processada_neste_obstaculo = True
                                break
                
                if acao_de_jogo_processada_neste_obstaculo or jogo_encerrar:
                    break

            if not desviou and not jogo_encerrar:
                colisoes += 1
                tocar_som("colisao")
            elif desviou and not jogo_encerrar:
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

            resultado = (f"Você fez {pontos} pontos no nível {nivel_final}.\nResultado copiado para a área de transferência.\n\n"
                        "Deseja jogar novamente?")

            resultado_completo = f"Dia {dia} de {mes_extenso} de {ano}, às {hora}:{minuto:02d}, {nome_computador} concluiu o jogo na dificuldade '{dificuldade_texto}' com {pontos} pontos, no nível {nivel_final}."

            pyperclip.copy(resultado_completo)
            print("Fim de jogo!")
            print("Resultado copiado para a área de transferência:")
            print(resultado_completo)

            jogar_novamente_dialog = DialogJogarNovamente(parent_window, resultado)
            res = jogar_novamente_dialog.ShowModal()
            jogar_novamente_dialog.Destroy()

            if res == wx.ID_YES:
                # O loop continua para uma nova rodada
                return nivel_dificuldade_escolhido
            else:
                # Encerra o jogo completamente
                return 0

        pygame.display.flip()
        pygame.time.Clock().tick(60)
    
    return 0

# Ponto de Entrada Principal
if __name__ == '__main__':
    app = wx.App(False)
    frame = wx.Frame(None) # Cria uma janela pai "invisível" para os dialogs
    
    try:
        while True:
            menu_principal_dialog = MenuPrincipal(frame)
            res_menu = menu_principal_dialog.ShowModal()
            nivel_dificuldade = menu_principal_dialog.nivel_dificuldade_escolhido
            menu_principal_dialog.Destroy()
            
            if res_menu == wx.ID_CANCEL or jogo_encerrar:
                break
            
            while True:
                nivel_selecionado = iniciar_jogo(frame, nivel_dificuldade)
                if nivel_selecionado == 0:
                    break
                else:
                    nivel_dificuldade = nivel_selecionado
        
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
    finally:
        if pygame.mixer.get_init():
            pygame.mixer.quit()
        if pygame.get_init():
            pygame.quit()
        
        # O aplicativo wxPython pode não estar rodando ao sair
        if wx.App.IsMainLoopRunning():
            app.ExitMainLoop()