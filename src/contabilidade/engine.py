"""Motor de calculo contabil - determinístico, sem LLM.

Regras centrais:
- Toda partida dobrada tem que fechar: soma dos debitos == soma dos creditos.
- O saldo de uma conta depende da sua natureza (Devedora: D - C; Credora: C - D).
- O balancete geral tem que fechar: soma de todos os debitos == soma de todos
  os creditos de todas as contas - se nao fechar, ha um erro na base, nao no
  calculo (todo lancamento individual ja e validado na entrada).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from .datasource import Conta, Partida

DUAS_CASAS = Decimal("0.01")


def buscar_conta(plano: list[Conta], codigo: str) -> Conta | None:
    for conta in plano:
        if conta.codigo == codigo:
            return conta
    return None


def validar_partidas(plano: list[Conta], linhas: list[dict]) -> tuple[bool, str | None]:
    """Valida uma lista de partidas de um lancamento antes de registrar.

    `linhas`: lista de dicts com conta (codigo), tipo ("D"/"C") e valor.
    Retorna (True, None) se valido, ou (False, motivo) caso contrario.
    """
    if len(linhas) < 2:
        return False, "Um lancamento precisa de pelo menos duas partidas (uma debito, uma credito)."

    total_debito = Decimal("0")
    total_credito = Decimal("0")

    for linha in linhas:
        codigo = str(linha.get("conta", "")).strip()
        tipo = str(linha.get("tipo", "")).strip().upper()
        valor = linha.get("valor")

        if tipo not in ("D", "C"):
            return False, f"Tipo de partida invalido para a conta {codigo!r}: {tipo!r} (use 'D' ou 'C')."

        conta = buscar_conta(plano, codigo)
        if conta is None:
            return False, f"Conta {codigo!r} nao existe no plano de contas."

        try:
            valor_decimal = Decimal(str(valor))
        except Exception:
            return False, f"Valor invalido para a conta {codigo!r}: {valor!r}."

        if valor_decimal <= 0:
            return False, f"Valor da partida na conta {codigo!r} tem que ser positivo."

        if tipo == "D":
            total_debito += valor_decimal
        else:
            total_credito += valor_decimal

    if total_debito.quantize(DUAS_CASAS) != total_credito.quantize(DUAS_CASAS):
        return False, (
            f"Partida dobrada nao fecha: total debito {total_debito} != total credito {total_credito}."
        )

    return True, None


def saldo_da_conta(conta: Conta, partidas: list[Partida], ate_data: date | None = None) -> dict:
    relevantes = [p for p in partidas if p.conta == conta.codigo and (ate_data is None or p.data <= ate_data)]
    total_debito = sum((p.valor for p in relevantes if p.tipo == "D"), Decimal("0"))
    total_credito = sum((p.valor for p in relevantes if p.tipo == "C"), Decimal("0"))

    if conta.natureza == "Devedora":
        saldo = total_debito - total_credito
    else:
        saldo = total_credito - total_debito

    return {
        "total_debito": total_debito,
        "total_credito": total_credito,
        "saldo": saldo,
        "quantidade_partidas": len(relevantes),
    }


def razao_da_conta(
    conta: Conta,
    partidas: list[Partida],
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> list[dict]:
    """Extrato da conta (razao): cada lancamento que a afeta, em ordem
    cronologica, com saldo acumulado apos cada partida."""
    relevantes = sorted(
        (
            p
            for p in partidas
            if p.conta == conta.codigo
            and (data_inicio is None or p.data >= data_inicio)
            and (data_fim is None or p.data <= data_fim)
        ),
        key=lambda p: (p.data, p.lancamento_id),
    )

    saldo_anterior = Decimal("0")
    if data_inicio is not None:
        # Saldo de tudo que veio ANTES de data_inicio (nao inclui o proprio dia,
        # que ja esta em `relevantes` e sera somado no loop abaixo).
        anteriores = [p for p in partidas if p.conta == conta.codigo and p.data < data_inicio]
        d = sum((p.valor for p in anteriores if p.tipo == "D"), Decimal("0"))
        c = sum((p.valor for p in anteriores if p.tipo == "C"), Decimal("0"))
        saldo_anterior = (d - c) if conta.natureza == "Devedora" else (c - d)

    saldo = saldo_anterior
    extrato = []
    for p in relevantes:
        movimento = p.valor if p.tipo == conta.natureza[0] else -p.valor
        saldo += movimento
        extrato.append(
            {
                "lancamento_id": p.lancamento_id,
                "data": p.data.isoformat(),
                "historico": p.historico,
                "tipo": p.tipo,
                "valor": str(p.valor),
                "saldo_apos": str(saldo),
            }
        )
    return extrato


def gerar_balancete(
    plano: list[Conta],
    partidas: list[Partida],
    data_inicio: date | None = None,
    data_fim: date | None = None,
    tipo: str | None = None,
) -> dict:
    """Balancete: total debito, total credito e saldo de cada conta, mais o
    fechamento geral (soma dos debitos == soma dos creditos de todas as contas)."""
    contas = [c for c in plano if tipo is None or c.tipo == tipo]

    if data_inicio is not None:
        partidas = [p for p in partidas if p.data >= data_inicio]
    if data_fim is not None:
        partidas = [p for p in partidas if p.data <= data_fim]

    linhas = []
    total_geral_debito = Decimal("0")
    total_geral_credito = Decimal("0")

    for conta in contas:
        resultado = saldo_da_conta(conta, partidas)
        if resultado["quantidade_partidas"] == 0:
            continue
        total_geral_debito += resultado["total_debito"]
        total_geral_credito += resultado["total_credito"]
        linhas.append(
            {
                "codigo": conta.codigo,
                "nome": conta.nome,
                "tipo": conta.tipo,
                "natureza": conta.natureza,
                "total_debito": str(resultado["total_debito"]),
                "total_credito": str(resultado["total_credito"]),
                "saldo": str(resultado["saldo"]),
            }
        )

    fecha = total_geral_debito.quantize(DUAS_CASAS) == total_geral_credito.quantize(DUAS_CASAS)

    return {
        "contas": linhas,
        "total_geral_debito": str(total_geral_debito),
        "total_geral_credito": str(total_geral_credito),
        "balancete_fecha": fecha,
    }
