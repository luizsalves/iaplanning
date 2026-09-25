"""Camada de acesso a dados do agente de conciliacao contabil.

Le o plano de contas e os lancamentos de CSVs fixture. Este modulo e
SOMENTE LEITURA - o agente nao tem nenhuma ferramenta que grave, altere ou
apague um lancamento. Ele consulta, valida (sem persistir) e gera
relatorios/razao/balancete a partir do que ja esta na base.
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
