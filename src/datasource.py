"""Camada de acesso a dados de contas a pagar.

Hoje le de um CSV fixture (data/contas_a_pagar.csv). O plano e trocar esta
fonte por uma leitura real do TOTVS RM assim que a conexao (banco, view ou
API) estiver definida - sem precisar mudar engine.py, tools.py nem agent.py,
que so conhecem a lista de dicts normalizada devolvida por `carregar_titulos`.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

CAMINHO_PADRAO = os.path.join(os.path.dirname(__file__), "..", "data", "contas_a_pagar.csv")

STATUS_VALIDOS = {"aberto", "parcial", "pago", "cancelado"}


@dataclass(frozen=True)
class Titulo:
    id: str
    fornecedor: str
    categoria: str
    empresa: str
    moeda: str
    vencimento: date
    valor_original: Decimal
    data_pagamento: date | None
    valor_pago: Decimal
    status: str
    juros: Decimal
    multa: Decimal
    desconto: Decimal

    @property
    def saldo_em_aberto(self) -> Decimal:
        if self.status not in ("aberto", "parcial"):
            return Decimal("0")
        return self.valor_original - self.valor_pago


def _parse_decimal(valor: str) -> Decimal:
    valor = (valor or "").strip()
    if not valor:
        return Decimal("0")
    try:
        return Decimal(valor)
    except InvalidOperation as exc:
        raise ValueError(f"Valor monetario invalido no dado de origem: {valor!r}") from exc


def _parse_data(valor: str) -> date | None:
    valor = (valor or "").strip()
    if not valor:
        return None
    return date.fromisoformat(valor)


def carregar_titulos(caminho: str | None = None) -> list[Titulo]:
    """Le e normaliza os titulos de contas a pagar da fonte configurada.

    Chamada a cada consulta (nao ha cache) para que, quando a fonte virar
    uma conexao real com o TOTVS RM, os dados retornados sejam sempre a
    leitura mais recente.
    """
    caminho = caminho or os.environ.get("CONTAS_A_PAGAR_CSV", CAMINHO_PADRAO)

    titulos: list[Titulo] = []
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        for linha in leitor:
            status = (linha["status"] or "").strip().lower()
            if status not in STATUS_VALIDOS:
                raise ValueError(f"Status desconhecido para o titulo {linha.get('id')}: {status!r}")
            titulos.append(
                Titulo(
                    id=linha["id"].strip(),
                    fornecedor=linha["fornecedor"].strip(),
                    categoria=linha["categoria"].strip(),
                    empresa=linha["empresa"].strip(),
                    moeda=linha["moeda"].strip(),
                    vencimento=_parse_data(linha["vencimento"]),
                    valor_original=_parse_decimal(linha["valor_original"]),
                    data_pagamento=_parse_data(linha["data_pagamento"]),
                    valor_pago=_parse_decimal(linha["valor_pago"]),
                    status=status,
                    juros=_parse_decimal(linha["juros"]),
                    multa=_parse_decimal(linha["multa"]),
                    desconto=_parse_decimal(linha["desconto"]),
                )
            )
    return titulos
