# Sistema Bancario Concorrente

Simulacao de um sistema bancario onde varios caixas (threads) depositam na mesma conta ao mesmo tempo, demonstrando conceitos de programacao concorrente.

## Conceitos demonstrados

| Conceito | No codigo | Descricao |
|----------|-----------|-----------|
| **Threads** | Cada caixa e uma thread | Executam depositos simultaneamente |
| **Memoria compartilhada** | `self.saldo` | Todas as threads leem e escrevem no mesmo atributo |
| **Race condition** | Modo "Sem protecao" | Depositos se perdem por acesso concorrente |
| **Lock** | `with self.lock` | Protege a regiao critica, garantindo uma thread por vez |
| **Queue** | `fila.put()` / `fila.get()` | Comunicacao segura entre threads e interface grafica |

## Como rodar

```bash
python banco.py
```

> O Tkinter ja vem instalado com o Python no Windows.
> No Linux, se faltar: `sudo apt install python3-tk`

## Como funciona

A interface permite escolher entre dois modos:

- **Sem protecao (com bug):** o deposito faz ler -> esperar -> gravar sem nenhuma trava. Outras threads podem ler o saldo antigo durante a espera, causando perda de depositos. O resultado varia a cada execucao.

- **Com Lock:** o deposito e protegido por um Lock (`threading.Lock`), garantindo que apenas uma thread por vez acesse o saldo. O resultado e sempre correto.

## Autores

- [Lukas](https://github.com/lukspec)
- [Willian Jeronimo Sousa da Silva](https://github.com/wlsousa1)
- [Jorge Felipe Afonso Walderrama](https://github.com/jorgewalderrama-del)
- [Luis Gustavo de Menezes Eggenstein](https://github.com/cocudiness)
- [Caio Marques Egidio](https://github.com/CaioEgidio)
