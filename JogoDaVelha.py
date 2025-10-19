import tkinter as tk
from tkinter import messagebox
import threading
import pygame
import os
from typing import List, Optional, Tuple

# ===== inicializa áudio de forma segura =====
try:
    pygame.mixer.init()
except Exception as e:
    print("Aviso: não foi possível inicializar áudio:", e)

click_sound = "click.wav"
victory_sound = "victory.wav"
draw_sound = "draw.wav"


def load_sound(path: str):
    if os.path.exists(path):
        try:
            return pygame.mixer.Sound(path)
        except Exception as e:
            print(f"Falha ao carregar som {path}: {e}")
    return None


class JogoDaVelha:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Jogo da Velha")

        # sons (podem ser None)
        self.som_clique = load_sound(click_sound)
        self.som_vitoria = load_sound(victory_sound)
        self.som_empate = load_sound(draw_sound)

        # estado do jogo
        self.tabuleiro: List[List[str]] = [
            ["" for _ in range(3)] for _ in range(3)]
        # botoes inicialmente None — serão criados no criar_interface
        self.botoes: List[List[Optional[tk.Button]]] = [
            [None for _ in range(3)] for _ in range(3)]

        self.rodada: str = "X"
        self.jogadas: int = 0
        self.placar = {"X": 0, "O": 0}
        self.modo: str = "IA"  # "IA" ou "2P"
        self.jogador_humano: str = "X"

        # flag para bloquear cliques enquanto a IA pensa
        self.ia_rodando: bool = False

        self.criar_interface()

    # ---------------- interface ----------------
    def criar_interface(self):
        frame_tabuleiro = tk.Frame(self.root)
        frame_tabuleiro.grid(row=0, column=0, padx=10, pady=10)

        for i in range(3):
            for j in range(3):
                botao = tk.Button(frame_tabuleiro, text="", font=("Arial", 24),
                                  width=5, height=2,
                                  command=lambda i=i, j=j: self.jogar(i, j))
                botao.grid(row=i, column=j, padx=5, pady=5)
                self.botoes[i][j] = botao  # sempre atribuímos botão aqui

        frame_controle = tk.Frame(self.root)
        frame_controle.grid(row=1, column=0, sticky="w")

        self.label_placar = tk.Label(
            frame_controle, text="Placar - X: 0 | O: 0", font=("Arial", 14))
        self.label_placar.grid(
            row=0, column=0, columnspan=3, pady=4, sticky="w")

        self.label_turno = tk.Label(
            frame_controle, text="Turno: X", font=("Arial", 12))
        self.label_turno.grid(row=1, column=0, sticky="w")

        tk.Label(frame_controle, text="Você joga como:").grid(
            row=2, column=0, sticky="w", pady=6)
        tk.Button(frame_controle, text="X", command=lambda: self.setar_jogador_humano(
            "X")).grid(row=2, column=1, sticky="w")
        tk.Button(frame_controle, text="O", command=lambda: self.setar_jogador_humano(
            "O")).grid(row=2, column=2, sticky="w")

        # Botões utilitários
        self.btn_modo = tk.Button(
            frame_controle, text="Modo: IA", command=self.toggle_modo)
        self.btn_modo.grid(row=3, column=0, pady=8, sticky="w")

        tk.Button(frame_controle, text="🔁 Reiniciar Jogo", command=self.reiniciar_tabuleiro).grid(
            row=3, column=1, pady=8, sticky="w")

    # ---------------- utilitários seguros ----------------
    def get_button(self, i: int, j: int) -> Optional[tk.Button]:
        """Retorna o botão se existir e for um tk.Button; senão None."""
        if 0 <= i < 3 and 0 <= j < 3:
            btn = self.botoes[i][j]
            if isinstance(btn, tk.Button):
                return btn
        return None

    def safe_config(self, btn: Optional[tk.Button], **kwargs):
        """Configura o botão somente se for um tk.Button (evita AttributeError)."""
        if isinstance(btn, tk.Button):
            try:
                btn.config(**kwargs)
            except Exception as e:
                print("Erro ao configurar botão:", e)

    def tocar_som(self, som):
        if som:
            try:
                threading.Thread(target=lambda: som.play(),
                                 daemon=True).start()
            except Exception:
                pass

    # ---------------- configuração ----------------
    def toggle_modo(self):
        self.modo = "2P" if self.modo == "IA" else "IA"
        self.btn_modo.config(text=f"Modo: {self.modo}")
        self.reiniciar_tabuleiro()

    def setar_jogador_humano(self, jogador: str):
        self.jogador_humano = jogador
        self.reiniciar_tabuleiro()

    # ---------------- jogar (human / UI) ----------------
    def jogar(self, i: int, j: int, by_ai: bool = False):
        """
        Aplica jogada na posição (i,j).
        by_ai=True quando a jogada vem da IA (para não ser bloqueada).
        """
        # Bloqueia cliques enquanto IA pensa (humanos)
        if self.ia_rodando and not by_ai:
            return

        # proteção: botão existe?
        btn = self.get_button(i, j)
        if btn is None:
            print(f"Aviso: botão ({i},{j}) inexistente.")
            return

        # checa espaço vazio
        if self.tabuleiro[i][j] != "":
            return

        # se modo IA, só impede humanos de jogar fora do turno (não impede IA)
        if (not by_ai) and self.modo == "IA" and self.rodada != self.jogador_humano:
            return

        # aplica jogada
        self.tabuleiro[i][j] = self.rodada
        self.safe_config(btn, text=self.rodada, state=tk.DISABLED)
        self.root.update_idletasks()  # força redraw
        self.tocar_som(self.som_clique)

        # verifica vitória
        if self.validar_vitoria(self.rodada):
            self.placar[self.rodada] += 1
            self.atualizar_placar()
            self.tocar_som(self.som_vitoria)
            self.animar_vitoria()
            # usa after para evitar reentrância com messagebox
            self.root.after(300, lambda: messagebox.showinfo(
                "Fim de Jogo", f"O jogador {self.rodada} venceu!"))
            self.root.after(350, self.reiniciar_tabuleiro)
            return

        # verifica empate
        self.jogadas += 1
        if self.jogadas == 9:
            self.tocar_som(self.som_empate)
            self.root.after(200, lambda: messagebox.showinfo(
                "Empate", "O jogo empatou!"))
            self.root.after(250, self.reiniciar_tabuleiro)
            return

        # alterna rodada
        self.rodada = "O" if self.rodada == "X" else "X"
        self.label_turno.config(text=f"Turno: {self.rodada}")

        # se modo IA e agora for vez da IA, disparar cálculo em background
        if self.modo == "IA" and self.rodada != self.jogador_humano:
            self.start_ai_thread()

    # ---------------- IA (thread + after) ----------------
    def start_ai_thread(self):
        if self.ia_rodando:
            return
        self.ia_rodando = True
        self.label_turno.config(text="IA pensando...")
        # desabilita botões vazios para evitar cliques
        self.set_buttons_state_disabled_for_empty()
        threading.Thread(target=self._compute_ai_move, daemon=True).start()

    def _compute_ai_move(self):
        ai_player = "O" if self.jogador_humano == "X" else "X"
        move = self.find_best_move(ai_player)
        # agenda aplicação da jogada na thread principal (Tkinter)
        self.root.after(0, lambda: self._apply_ai_move(move))

    def _apply_ai_move(self, move: Tuple[Optional[int], Optional[int]]):
        # IA terminou (agora é seguro permitir cliques)
        # Mantemos ia_rodando False antes de chamar jogar com by_ai=True
        self.ia_rodando = False
        # reabilita botões vazios (caso necessário)
        self.set_buttons_state_enabled_for_empty()
        i, j = move
        if i is not None and j is not None:
            # chama jogar informando que é IA
            self.jogar(i, j, by_ai=True)

    def set_buttons_state_disabled_for_empty(self):
        for a in range(3):
            for b in range(3):
                btn = self.get_button(a, b)
                if btn and self.tabuleiro[a][b] == "":
                    self.safe_config(btn, state=tk.DISABLED)

    def set_buttons_state_enabled_for_empty(self):
        for a in range(3):
            for b in range(3):
                btn = self.get_button(a, b)
                if btn and self.tabuleiro[a][b] == "":
                    self.safe_config(btn, state=tk.NORMAL)

    # ---------------- Minimax com poda alfa-beta ----------------
    def find_best_move(self, ai_player: str) -> Tuple[Optional[int], Optional[int]]:
        best_val = -999
        best_move: Tuple[Optional[int], Optional[int]] = (None, None)

        empties = [(i, j) for i in range(3)
                   for j in range(3) if self.tabuleiro[i][j] == ""]
        # pequena heurística: se tabuleiro vazio, escolha centro
        if len(empties) == 9:
            return (1, 1)

        for i, j in empties:
            self.tabuleiro[i][j] = ai_player
            val = self.minimax(False, ai_player, -999, 999)
            self.tabuleiro[i][j] = ""
            if val > best_val:
                best_val = val
                best_move = (i, j)
        return best_move

    def minimax(self, is_maximizing: bool, ai_player: str, alpha: int, beta: int) -> int:
        """Retorna pontuação: 10 (ai vence), -10 (oponente vence), 0 empate."""
        opponent = "X" if ai_player == "O" else "O"

        if self.validar_vitoria(ai_player):
            return 10
        if self.validar_vitoria(opponent):
            return -10
        if all(self.tabuleiro[i][j] != "" for i in range(3) for j in range(3)):
            return 0

        if is_maximizing:
            best = -999
            for i in range(3):
                for j in range(3):
                    if self.tabuleiro[i][j] == "":
                        self.tabuleiro[i][j] = ai_player
                        val = self.minimax(False, ai_player, alpha, beta)
                        self.tabuleiro[i][j] = ""
                        best = max(best, val)
                        alpha = max(alpha, best)
                        if beta <= alpha:
                            break
                if beta <= alpha:
                    break
            return best
        else:
            best = 999
            for i in range(3):
                for j in range(3):
                    if self.tabuleiro[i][j] == "":
                        self.tabuleiro[i][j] = opponent
                        val = self.minimax(True, ai_player, alpha, beta)
                        self.tabuleiro[i][j] = ""
                        best = min(best, val)
                        beta = min(beta, best)
                        if beta <= alpha:
                            break
                if beta <= alpha:
                    break
            return best

    # ---------------- validação e UI ----------------
    def validar_vitoria(self, jogador: str) -> bool:
        t = self.tabuleiro
        for i in range(3):
            if all(t[i][j] == jogador for j in range(3)):
                return True
            if all(t[j][i] == jogador for j in range(3)):
                return True
        if t[0][0] == jogador and t[1][1] == jogador and t[2][2] == jogador:
            return True
        if t[0][2] == jogador and t[1][1] == jogador and t[2][0] == jogador:
            return True
        return False

    def reiniciar_tabuleiro(self):
        # garante que a IA não fique marcada como rodando
        self.ia_rodando = False
        self.tabuleiro = [["" for _ in range(3)] for _ in range(3)]
        self.jogadas = 0
        self.rodada = "X"
        self.label_turno.config(text=f"Turno: {self.rodada}")
        default_bg = self.root.cget("bg") or "SystemButtonFace"
        for i in range(3):
            for j in range(3):
                btn = self.get_button(i, j)
                if btn:
                    self.safe_config(
                        btn, text="", state=tk.NORMAL, bg=default_bg)

        # se modo IA e humano escolheu O, IA começa
        if self.modo == "IA" and self.jogador_humano != "X":
            self.root.after(300, self.start_ai_thread)

    def atualizar_placar(self):
        self.label_placar.config(
            text=f"Placar - X: {self.placar['X']} | O: {self.placar['O']}")

    def animar_vitoria(self):
        def piscar(count: int):
            cor = "lightgreen" if count % 2 == 0 else (
                self.root.cget("bg") or "SystemButtonFace")
            for i in range(3):
                for j in range(3):
                    btn = self.get_button(i, j)
                    if btn:
                        self.safe_config(btn, bg=cor)
            if count > 0:
                self.root.after(200, piscar, count - 1)
            else:
                default_bg = self.root.cget("bg") or "SystemButtonFace"
                for i in range(3):
                    for j in range(3):
                        btn = self.get_button(i, j)
                        if btn:
                            self.safe_config(btn, bg=default_bg)
        piscar(6)


# ===== executa =====
if __name__ == "__main__":
    root = tk.Tk()
    jogo = JogoDaVelha(root)
    root.mainloop()
