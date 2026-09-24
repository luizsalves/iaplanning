"""Interface de linha de comando do agente de Conciliacao Contabil.

Uso interativo (dentro do container):
    python -m src.contabilidade.cli

Uso direto (um pedido so, util para testar/scriptar):
    python -m src.contabilidade.cli "Gere o balancete de setembro"
    python -m src.contabilidade.cli "Lance o pagamento de energia" --arquivo docs_enviados/nota.pdf

No modo interativo, anexe um arquivo antes do pedido com:
    /arquivo docs_enviados/extrato.pdf
"""

from __future__ import annotations

import argparse
import sys

from .agent import perguntar

AJUDA = (
    "Comandos:\n"
    "  /arquivo <caminho>   anexa um arquivo ao proximo pedido (PDF, imagem, CSV/TXT/OFX)\n"
    "  /ajuda               mostra esta mensagem\n"
    "  /sair                encerra\n"
)


def _modo_interativo() -> None:
    print("Especialista em Conciliacao Contabil - digite /ajuda para ver os comandos.\n")
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
            print(f"[arquivo anexado para o proximo pedido: {arquivo_pendente}]")
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
    parser = argparse.ArgumentParser(description="Agente de Conciliacao Contabil")
    parser.add_argument("pedido", nargs="?", help="Pergunta ou pedido unico (modo nao interativo)")
    parser.add_argument("--arquivo", help="Caminho de um arquivo para anexar ao pedido")
    args = parser.parse_args()

    if args.pedido:
        print(perguntar(args.pedido, arquivo=args.arquivo))
        return

    if not sys.stdin.isatty():
        parser.error("Sem TTY e sem pedido na linha de comando - nada para fazer.")

    _modo_interativo()


if __name__ == "__main__":
    main()
