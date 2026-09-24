"""Camada de acesso a dados do agente de conciliacao contabil.

Le o plano de contas e os lancamentos de CSVs fixture. `registrar_lancamento`
e a unica escrita permitida: acrescenta linhas ao final do CSV de
lancamentos, uma por partida, e nunca reescreve o que ja existe.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

DIR_DADOS = os.path.join(os.path.dirname(__file__), "..", "..", "data", "contabilidade")
CAMINHO_PLANO_DE_CONTAS = os.path.join(DIR_DADOS, "plano_de_contas.csv")
CAMINHO_LANCAMENTOS = os.path.join(DIR_DADOS, "lancamentos.csv")

TIPOS_VALIDOS = {"Ativo", "Passivo", "Patrimonio Liquido", "Receita", "Despesa"}
NATUREZAS_VALIDAS = {"Devedora", "Credora"}
TIPOS_PARTIDA_VALIDOS = {"D", "C"}


@dataclass(frozen=True)
class Conta:
    codigo: str
    nome: str
    tipo: str
    natureza: str


@dataclass(frozen=True)
class Partida:
    lancamento_id: str
    data: date
    historico: str
    conta: str
    tipo: str  # "D" ou "C"
    valor: Decimal


def _parse_decimal(valor: str) -> Decimal:
    valor = (valor or "").strip()
    try:
        return Decimal(valor)
    except InvalidOperation as exc:
        raise ValueError(f"Valor monetario invalido no dado de origem: {valor!r}") from exc


def carregar_plano_de_contas(caminho: str | None = None) -> list[Conta]:
    caminho = caminho or os.environ.get("CONTABILIDADE_PLANO_CSV", CAMINHO_PLANO_DE_CONTAS)
    contas = []
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            tipo = linha["tipo"].strip()
            natureza = linha["natureza"].strip()
            if tipo not in TIPOS_VALIDOS:
                raise ValueError(f"Tipo de conta desconhecido para {linha.get('codigo')}: {tipo!r}")
            if natureza not in NATUREZAS_VALIDAS:
                raise ValueError(f"Natureza desconhecida para {linha.get('codigo')}: {natureza!r}")
            contas.append(Conta(codigo=linha["codigo"].strip(), nome=linha["nome"].strip(), tipo=tipo, natureza=natureza))
    return contas


def carregar_lancamentos(caminho: str | None = None) -> list[Partida]:
    caminho = caminho or os.environ.get("CONTABILIDADE_LANCAMENTOS_CSV", CAMINHO_LANCAMENTOS)
    partidas = []
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            tipo = linha["tipo"].strip().upper()
            if tipo not in TIPOS_PARTIDA_VALIDOS:
                raise ValueError(f"Tipo de partida invalido em {linha.get('lancamento_id')}: {tipo!r}")
            partidas.append(
                Partida(
                    lancamento_id=linha["lancamento_id"].strip(),
                    data=date.fromisoformat(linha["data"].strip()),
                    historico=linha["historico"].strip(),
                    conta=linha["conta"].strip(),
                    tipo=tipo,
                    valor=_parse_decimal(linha["valor"]),
                )
            )
    return partidas


def _proximo_lancamento_id(partidas: list[Partida]) -> str:
    maior = 0
    for p in partidas:
        try:
            numero = int(p.lancamento_id.split("-")[-1])
        except ValueError:
            continue
        maior = max(maior, numero)
    return f"LC-{maior + 1:04d}"


def registrar_lancamento(
    data_lancamento: date,
    historico: str,
    linhas: list[dict],
    *,
    caminho: str | None = None,
) -> str:
    """Acrescenta um lancamento (ja validado pelo chamador) ao CSV.

    `linhas` e uma lista de dicts com chaves conta/tipo/valor - a mesma
    forma normalizada usada por engine.validar_partidas. Esta funcao nao
    valida partida dobrada de novo; quem chama (tools.py) ja deve ter
    validado antes de persistir.
    """
    caminho = caminho or os.environ.get("CONTABILIDADE_LANCAMENTOS_CSV", CAMINHO_LANCAMENTOS)
    lancamento_id = _proximo_lancamento_id(carregar_lancamentos(caminho))

    with open(caminho, "a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        for linha in linhas:
            escritor.writerow(
                [
                    lancamento_id,
                    data_lancamento.isoformat(),
                    historico,
                    linha["conta"],
                    linha["tipo"],
                    str(linha["valor"]),
                ]
            )
    return lancamento_id
