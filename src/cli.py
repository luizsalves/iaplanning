"""Interface de linha de comando para conversar com o agente localmente.

Uso interativo (dentro do container):
    python -m src.cli

Uso direto (uma pergunta so, util para testar/scriptar):
    python -m src.cli "Qual o total vencido?"
    python -m src.cli "Projete meu saldo" --arquivo docs_enviados/extrato.pdf

No modo interativo, anexe um arquivo antes da pergunta com:
    /arquivo docs_enviados/extrato.pdf
"""

from __future__ import annotations

import argparse
import sys

from .agent import perguntar

AJUDA = (
    "Comandos:\n"
    "  /arquivo <caminho>   anexa um arquivo a proxima pergunta (PDF, imagem, CSV/TXT/OFX)\n"
    "  /ajuda               mostra esta mensagem\n"
    "  /sair                encerra\n"
)


def _modo_interativo() -> None:
    print("Especialista de Contas a Pagar - digite /ajuda para ver os comandos.\n")
    arquivo_pendente: str | None = None

    while True:
        try:
            entrada = input("voce> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not entrada:
            continue
        if entrada in ("/sair", "/exit", "/quit"):
            break
        if entrada == "/ajuda":
            print(AJUDA)
            continue
        if entrada.startswith("/arquivo "):
            arquivo_pendente = entrada.removeprefix("/arquivo ").strip()
            print(f"[arquivo anexado para a proxima pergunta: {arquivo_pendente}]")
            continue

        try:
            resposta = perguntar(entrada, arquivo=arquivo_pendente)
        except Exception as exc:  # noqa: BLE001 - queremos mostrar qualquer erro ao usuario local
            print(f"[erro] {exc}")
        else:
            print(f"\nagente> {resposta}\n")
        finally:
            arquivo_pendente = None


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente de Contas a Pagar")
    parser.add_argument("pergunta", nargs="?", help="Pergunta unica (modo nao interativo)")
    parser.add_argument("--arquivo", help="Caminho de um arquivo para anexar a pergunta")
    args = parser.parse_args()

    if args.pergunta:
        print(perguntar(args.pergunta, arquivo=args.arquivo))
        return

    if not sys.stdin.isatty():
        parser.error("Sem TTY e sem pergunta na linha de comando - nada para fazer.")

    _modo_interativo()


if __name__ == "__main__":
    main()
