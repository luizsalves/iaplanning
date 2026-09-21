"""Motor de calculo de contas a pagar - a parte 'Financial Engine' em miniatura.

Toda funcao aqui e determinística: mesma entrada, mesma saida, sem LLM
envolvido. O agente (src/agent.py) so pode obter numeros atraves das
ferramentas em src/tools.py, que chamam estas funcoes.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from .datasource import Titulo

ABERTOS = ("aberto", "parcial")


def _ativos(titulos: list[Titulo]) -> list[Titulo]:
    return [t for t in titulos if t.status != "cancelado"]


def filtrar(
    titulos: list[Titulo],
    *,
    empresa: str | None = None,
    fornecedor: str | None = None,
    categoria: str | None = None,
    status: str | None = None,
) -> list[Titulo]:
    resultado = _ativos(titulos)
    if empresa:
        resultado = [t for t in resultado if t.empresa.lower() == empresa.lower()]
    if fornecedor:
        alvo = fornecedor.lower()
        resultado = [t for t in resultado if alvo in t.fornecedor.lower()]
    if categoria:
        resultado = [t for t in resultado if t.categoria.lower() == categoria.lower()]
    if status:
        resultado = [t for t in resultado if t.status == status.lower()]
    return resultado


def total_em_aberto(titulos: list[Titulo], *, empresa: str | None = None, categoria: str | None = None) -> Decimal:
    filtrados = filtrar(titulos, empresa=empresa, categoria=categoria)
    return sum((t.saldo_em_aberto for t in filtrados if t.status in ABERTOS), Decimal("0"))


def total_vencido(titulos: list[Titulo], data_referencia: date, *, empresa: str | None = None) -> Decimal:
    filtrados = filtrar(titulos, empresa=empresa)
    return sum(
        (t.saldo_em_aberto for t in filtrados if t.status in ABERTOS and t.vencimento < data_referencia),
        Decimal("0"),
    )


def total_a_vencer(
    titulos: list[Titulo],
    data_referencia: date,
    dias: int,
    *,
    empresa: str | None = None,
) -> Decimal:
    limite = data_referencia + timedelta(days=dias)
    filtrados = filtrar(titulos, empresa=empresa)
    return sum(
        (
            t.saldo_em_aberto
            for t in filtrados
            if t.status in ABERTOS and data_referencia <= t.vencimento <= limite
        ),
        Decimal("0"),
    )


def total_pago_no_mes(
    titulos: list[Titulo],
    ano_mes: str,
    *,
    empresa: str | None = None,
) -> Decimal:
    """ano_mes no formato 'YYYY-MM'."""
    filtrados = filtrar(titulos, empresa=empresa, status="pago")
    return sum(
        (
            t.valor_pago
            for t in filtrados
            if t.data_pagamento and t.data_pagamento.strftime("%Y-%m") == ano_mes
        ),
        Decimal("0"),
    )


def resumo_por_categoria(titulos: list[Titulo], *, empresa: str | None = None) -> list[dict]:
    filtrados = filtrar(titulos, empresa=empresa)
    categorias = sorted({t.categoria for t in filtrados})
    resumo = []
    for categoria in categorias:
        do_grupo = [t for t in filtrados if t.categoria == categoria]
        resumo.append(
            {
                "categoria": categoria,
                "total_em_aberto": str(sum((t.saldo_em_aberto for t in do_grupo if t.status in ABERTOS), Decimal("0"))),
                "total_pago": str(sum((t.valor_pago for t in do_grupo if t.status == "pago"), Decimal("0"))),
                "quantidade_titulos": len(do_grupo),
            }
        )
    return resumo


def detectar_atrasos(titulos: list[Titulo], data_referencia: date, *, empresa: str | None = None) -> list[dict]:
    filtrados = filtrar(titulos, empresa=empresa)
    atrasados = [t for t in filtrados if t.status in ABERTOS and t.vencimento < data_referencia]
    atrasados.sort(key=lambda t: t.vencimento)
    return [
        {
            "id": t.id,
            "fornecedor": t.fornecedor,
            "empresa": t.empresa,
            "categoria": t.categoria,
            "vencimento": t.vencimento.isoformat(),
            "dias_atraso": (data_referencia - t.vencimento).days,
            "saldo_em_aberto": str(t.saldo_em_aberto),
        }
        for t in atrasados
    ]


def comparar_periodos(titulos: list[Titulo], periodo_1: str, periodo_2: str, *, empresa: str | None = None) -> dict:
    return {
        "periodo_1": {"periodo": periodo_1, "total_pago": str(total_pago_no_mes(titulos, periodo_1, empresa=empresa))},
        "periodo_2": {"periodo": periodo_2, "total_pago": str(total_pago_no_mes(titulos, periodo_2, empresa=empresa))},
    }


def projetar_saldo(
    titulos: list[Titulo],
    saldo_inicial: Decimal,
    data_saldo: date,
    dias: int,
    *,
    empresa: str | None = None,
) -> dict:
    """Projeta o saldo de caixa para frente, liquido das obrigacoes ja registradas.

    `saldo_inicial` e `data_saldo` vem do extrato bancario que o usuario
    anexou (extraidos pelo agente, nunca calculados por ele). Esta funcao
    apenas cruza esse saldo com os titulos em aberto/parcial da base.
    """
    filtrados = filtrar(titulos, empresa=empresa)
    obrigacoes = [t for t in filtrados if t.status in ABERTOS]

    # <=: inclui tambem o que vence exatamente na data do extrato - na pratica
    # essa saida ja deveria estar refletida (ou prestes a ser) no saldo do banco.
    vencidas_nao_pagas = sum(
        (t.saldo_em_aberto for t in obrigacoes if t.vencimento <= data_saldo),
        Decimal("0"),
    )

    projecao = []
    saida_acumulada = Decimal("0")
    for i in range(1, dias + 1):
        dia = data_saldo + timedelta(days=i)
        saida_do_dia = sum((t.saldo_em_aberto for t in obrigacoes if t.vencimento == dia), Decimal("0"))
        saida_acumulada += saida_do_dia
        projecao.append(
            {
                "data": dia.isoformat(),
                "saida_do_dia": str(saida_do_dia),
                "saida_acumulada": str(saida_acumulada),
                "saldo_projetado": str(saldo_inicial - saida_acumulada),
            }
        )

    return {
        "data_saldo": data_saldo.isoformat(),
        "saldo_inicial": str(saldo_inicial),
        "empresa": empresa,
        "obrigacoes_vencidas_nao_pagas_ate_data_saldo": str(vencidas_nao_pagas),
        "projecao_dias": projecao,
        "observacao": (
            "Projecao considera apenas titulos ja registrados na base (status aberto/parcial). "
            "Nao inclui entradas previstas (contas a receber) nem despesas ainda nao lancadas - "
            "por isso o saldo projetado tende a ser mais pessimista que o real se houver recebimentos no periodo."
        ),
    }
