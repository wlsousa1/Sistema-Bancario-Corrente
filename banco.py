"""
Sistema Bancario Concorrente - versao com interface grafica (Tkinter)
---------------------------------------------------------------------
Demonstra threads, memoria compartilhada e sincronizacao.

  - Varios caixas (threads) depositam na MESMA conta.
    A conta (self.saldo) e a MEMORIA COMPARTILHADA.
  - Sem protecao  -> race condition: o saldo final fica errado e muda toda vez.
  - Com Lock      -> regiao critica protegida: o saldo final fecha sempre certo.
  - A comunicacao entre as threads e a tela usa uma QUEUE (fila thread-safe),
    porque o Tkinter so pode ser atualizado pela thread principal.

Resumo dos requisitos da atividade atendidos:
  threads .......... varios caixas rodando ao mesmo tempo
  memoria compart. . o atributo self.saldo
  Lock ............. protege o "ler-somar-gravar" do saldo
  Queue ............ leva os eventos das threads para a interface

Como rodar no VS Code:
  basta abrir este arquivo e apertar "Run" (ou: python banco_gui.py)
  O Tkinter ja vem com o Python no Windows.
  (No Linux, se faltar: sudo apt install python3-tk)
"""

import tkinter as tk
from tkinter import ttk
import threading
import queue
import time
import random

# atraso por deposito, so para a concorrencia ficar visivel na tela
ATRASO = 0.05


class ContaBancaria:
    def __init__(self):
        self.saldo = 0                 # <<< MEMORIA COMPARTILHADA
        self.lock = threading.Lock()   # cadeado que protege o saldo
        # Simula condicoes diferentes do sistema a cada execucao:
        # carga alta = processamento lento = mais colisoes entre threads
        # carga baixa = processamento rapido = menos colisoes
        self.carga = random.random()   # 0.0 a 1.0

    def depositar_sem_lock(self, valor):
        # ler -> somar -> gravar NAO e atomico: outra thread pode entrar no meio
        atual = self.saldo             # 1) le
        # 2) Carga controla probabilidade E duracao do atraso:
        #    carga baixa = poucos sleeps curtos = quase sem colisao
        #    carga alta  = muitos sleeps longos = colisao massiva
        if random.random() < self.carga:
            time.sleep(self.carga * ATRASO * 3)
        self.saldo = atual + valor     # 3) grava (pode estar desatualizado)

    def depositar_com_lock(self, valor):
        with self.lock:                # <<< REGIAO CRITICA: uma thread por vez
            atual = self.saldo
            time.sleep(ATRASO)
            self.saldo = atual + valor


def caixa_trabalhando(conta, caixa_id, n_dep, valor, usar_lock, fila):
    """Funcao executada por cada thread (caixa)."""
    feitos = 0
    for _ in range(n_dep):
        if usar_lock:
            conta.depositar_com_lock(valor)
        else:
            conta.depositar_sem_lock(valor)
        feitos += 1
        # avisa a interface pela Queue (nao mexe na tela direto: nao seria seguro)
        fila.put(("caixa", caixa_id, feitos, "trabalhando"))
        fila.put(("saldo", conta.saldo))
    fila.put(("caixa", caixa_id, feitos, "concluido"))
    fila.put(("fim_thread",))


class Aplicacao:
    def __init__(self, root):
        self.root = root
        root.title("Sistema Bancario Concorrente")
        root.geometry("660x640")
        root.minsize(640, 600)

        self.fila = queue.Queue()
        self.conta = None
        self.esperado = 0
        self.total_threads = 0
        self.threads_terminadas = 0
        self.depositos_totais = 0
        self.rodando = False

        self.usar_lock = tk.BooleanVar(value=False)
        self.n_caixas = tk.IntVar(value=5)
        self.n_dep = tk.IntVar(value=10)

        self._montar_ui()
        self.root.after(60, self._processar_fila)

    # ------------------------------------------------------------------ UI
    def _montar_ui(self):
        tk.Label(self.root, text="Sistema Bancario Concorrente",
                 font=("Segoe UI", 16, "bold")).pack(pady=(14, 2))
        tk.Label(self.root, text="Varios caixas (threads) depositando na mesma conta",
                 font=("Segoe UI", 10), fg="#666").pack()

        ctrl = ttk.LabelFrame(self.root, text="Controles")
        ctrl.pack(fill="x", padx=14, pady=12)

        modo = ttk.Frame(ctrl)
        modo.pack(fill="x", padx=8, pady=6)
        ttk.Label(modo, text="Modo:").pack(side="left")
        ttk.Radiobutton(modo, text="Sem protecao (com bug)",
                        variable=self.usar_lock, value=False).pack(side="left", padx=8)
        ttk.Radiobutton(modo, text="Com Lock",
                        variable=self.usar_lock, value=True).pack(side="left", padx=8)

        nums = ttk.Frame(ctrl)
        nums.pack(fill="x", padx=8, pady=6)
        ttk.Label(nums, text="Caixas (threads):").pack(side="left")
        ttk.Spinbox(nums, from_=2, to=10, width=5,
                    textvariable=self.n_caixas).pack(side="left", padx=6)
        ttk.Label(nums, text="Depositos por caixa:").pack(side="left", padx=(14, 0))
        ttk.Spinbox(nums, from_=1, to=50, width=5,
                    textvariable=self.n_dep).pack(side="left", padx=6)

        botoes = ttk.Frame(ctrl)
        botoes.pack(fill="x", padx=8, pady=(6, 8))
        self.btn_run = ttk.Button(botoes, text="Executar", command=self.executar)
        self.btn_run.pack(side="left")
        self.btn_reset = ttk.Button(botoes, text="Resetar", command=self.resetar)
        self.btn_reset.pack(side="left", padx=8)

        self.lbl_saldo = tk.Label(self.root, text="R$ 0", font=("Segoe UI", 32, "bold"))
        self.lbl_saldo.pack(pady=(8, 0))
        tk.Label(self.root, text="saldo compartilhado (memoria compartilhada)",
                 font=("Segoe UI", 9), fg="#888").pack()

        met = ttk.Frame(self.root)
        met.pack(pady=12)
        self.lbl_esp = self._metrica(met, "Esperado", 0)
        self.lbl_atual = self._metrica(met, "Atual", 1)
        self.lbl_perd = self._metrica(met, "Perdidos", 2, cor="#c0392b")

        self.tabela = ttk.Treeview(self.root, columns=("dep", "status"), height=6)
        self.tabela.heading("#0", text="Caixa")
        self.tabela.heading("dep", text="Depositos feitos")
        self.tabela.heading("status", text="Status")
        self.tabela.column("#0", width=130, anchor="center")
        self.tabela.column("dep", width=150, anchor="center")
        self.tabela.column("status", width=170, anchor="center")
        self.tabela.pack(fill="x", padx=14, pady=(0, 8))

        self.lbl_banner = tk.Label(self.root, text="", font=("Segoe UI", 10, "bold"),
                                   wraplength=620, justify="center")
        self.lbl_banner.pack(pady=6)

    def _metrica(self, parent, titulo, col, cor="#000000"):
        f = ttk.Frame(parent)
        f.grid(row=0, column=col, padx=20)
        ttk.Label(f, text=titulo, font=("Segoe UI", 9)).pack()
        lbl = tk.Label(f, text="0", font=("Segoe UI", 20, "bold"), fg=cor)
        lbl.pack()
        return lbl

    # -------------------------------------------------------------- acoes
    def executar(self):
        if self.rodando:
            return
        self.resetar()
        self.rodando = True
        self.btn_run.state(["disabled"])

        n = self.n_caixas.get()
        d = self.n_dep.get()
        usar = self.usar_lock.get()

        self.esperado = n * d
        self.total_threads = n
        self.threads_terminadas = 0
        self.depositos_totais = 0
        self.conta = ContaBancaria()

        self.lbl_esp.config(text=str(self.esperado))
        self.lbl_saldo.config(fg="#000000")
        self.lbl_banner.config(text="Rodando...", fg="#555555")

        for i in range(1, n + 1):
            self.tabela.insert("", "end", iid=str(i),
                               text=f"Caixa {i}", values=(0, "esperando"))

        for i in range(1, n + 1):
            t = threading.Thread(
                target=caixa_trabalhando,
                args=(self.conta, i, d, 1, usar, self.fila),
                daemon=True,
            )
            t.start()

    def resetar(self):
        self.rodando = False
        try:
            while True:
                self.fila.get_nowait()
        except queue.Empty:
            pass
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        self.depositos_totais = 0
        self.lbl_saldo.config(text="R$ 0", fg="#000000")
        self.lbl_atual.config(text="0")
        self.lbl_perd.config(text="0")
        self.lbl_banner.config(text="")
        self.btn_run.state(["!disabled"])

    # --------------------------------------------------- ponte Queue->tela
    def _processar_fila(self):
        try:
            while True:
                msg = self.fila.get_nowait()
                tipo = msg[0]

                if tipo == "saldo":
                    saldo = msg[1]
                    self.depositos_totais += 1
                    self.lbl_saldo.config(text=f"R$ {saldo}")
                    self.lbl_atual.config(text=str(saldo))
                    self.lbl_perd.config(text=str(max(0, self.depositos_totais - saldo)))

                elif tipo == "caixa":
                    _, cid, feitos, status = msg
                    if self.tabela.exists(str(cid)):
                        self.tabela.item(str(cid), values=(feitos, status))

                elif tipo == "fim_thread":
                    self.threads_terminadas += 1
                    if self.threads_terminadas >= self.total_threads:
                        self._finalizar()
        except queue.Empty:
            pass
        self.root.after(60, self._processar_fila)

    def _finalizar(self):
        self.rodando = False
        self.btn_run.state(["!disabled"])
        saldo = self.conta.saldo
        perdidos = self.esperado - saldo
        if self.usar_lock.get():
            self.lbl_saldo.config(fg="#1e8449")
            self.lbl_banner.config(
                text=(f"COM LOCK: saldo final R$ {saldo} de R$ {self.esperado}. "
                      "Nenhum deposito perdido - o Lock protegeu a regiao critica."),
                fg="#1e8449")
        else:
            self.lbl_saldo.config(fg="#c0392b")
            self.lbl_banner.config(
                text=(f"SEM PROTECAO: saldo final R$ {saldo} de R$ {self.esperado}. "
                      f"{perdidos} deposito(s) sumiram pela race condition. "
                      "Rode de novo: o numero muda."),
                fg="#c0392b")


if __name__ == "__main__":
    root = tk.Tk()
    Aplicacao(root)
    root.mainloop()
