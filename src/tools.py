"""Ferramentas expostas ao agente. Sao a unica forma de o LLM tocar em dados
reais - todo numero na resposta final tem que vir de uma chamada aqui."""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal, InvalidOperation

from anthropic import beta_tool

from . import engine
from .datasource import carregar_titulos

INDICADORES_DISPONIVEIS = (
    "total_em_aberto",
    "total_vencido",
    "total_a_vencer_hoje",
    "total_a_vencer_7_dias",
    "total_pago_mes_atual",
)


def data_referencia_atual() -> date:
    valor = os.environ.get("CONTAS_A_PAGAR_DATA_REF")
    if valor:
        return date.fromisoformat(valor)
    return date.today()


def _decimal(valor: float | str) -> Decimal:
    try:
        return Decimal(str(valor))
    except InvalidOperation as exc:
        raise ValueError(f"Valor monetario invalido: {valor!r}") from exc


@beta_tool
def get_indicador(nome: str, empresa: str = "") -> dict:
    """Retorna o valor de um indicador financeiro fixo de contas a pagar.

    Chame esta ferramenta sempre que o usuario perguntar sobre um numero
    consolidado (total em aberto, total vencido, quanto vence hoje ou nos
    proximos 7 dias, quanto foi pago no mes de referencia). Nunca estime
    esses valores por conta propria.

    Args:
        nome: Um dos indicadores fixos: total_em_aberto, total_vencido,
            total_a_vencer_hoje, total_a_vencer_7_dias, total_pago_mes_atual.
        empresa: Filtra por empresa (ex: "Empresa A"). Deixe vazio para o
            grupo consolidado.
    """
    if nome not in INDICADORES_DISPONIVEIS:
        return {
            "erro": f"Indicador desconhecido: {nome!r}.",
            "indicadores_disponiveis": list(INDICADORES_DISPONIVEIS),
        }

    titulos = carregar_titulos()
    hoje = data_referencia_atual()
    emp = empresa or None

    if nome == "total_em_aberto":
        valor = engine.total_em_aberto(titulos, empresa=emp)
    elif nome == "total_vencido":
        valor = engine.total_vencido(titulos, hoje, empresa=emp)
    elif nome == "total_a_vencer_hoje":
        valor = engine.total_a_vencer(titulos, hoje, 0, empresa=emp)
    elif nome == "total_a_vencer_7_dias":
        valor = engine.total_a_vencer(titulos, hoje, 7, empresa=emp)
    elif nome == "total_pago_mes_atual":
        valor = engine.total_pago_no_mes(titulos, hoje.strftime("%Y-%m"), empresa=emp)

    return {
        "indicador": nome,
        "empresa": empresa or "consolidado",
        "data_referencia": hoje.isoformat(),
        "valor": str(valor),
        "moeda": "BRL",
    }


@beta_tool
def listar_titulos(
    status: str = "",
    empresa: str = "",
    fornecedor: str = "",
    categoria: str = "",
) -> dict:
    """Lista titulos de contas a pagar que atendem aos filtros informados.

    Use para responder perguntas sobre um fornecedor especifico, uma
    categoria de despesa, ou para listar tudo que esta em aberto/vencido/
    pago/parcial. Deixe um filtro vazio para nao aplica-lo.

    Args:
        status: aberto, parcial, pago ou cancelado. Vazio = todos (exceto cancelado).
        empresa: Nome exato da empresa (ex: "Empresa A"). Vazio = todas.
        fornecedor: Trecho do nome do fornecedor (busca parcial, sem case). Vazio = todos.
        categoria: Nome exato da categoria (ex: "Aluguel", "Impostos"). Vazio = todas.
    """
    titulos = carregar_titulos()
    filtrados = engine.filtrar(
        titulos,
        empresa=empresa or None,
        fornecedor=fornecedor or None,
        categoria=categoria or None,
        status=status or None,
    )
    return {
        "quantidade": len(filtrados),
        "titulos": [
            {
                "id": t.id,
                "fornecedor": t.fornecedor,
                "categoria": t.categoria,
                "empresa": t.empresa,
                "vencimento": t.vencimento.isoformat(),
                "valor_original": str(t.valor_original),
                "valor_pago": str(t.valor_pago),
                "saldo_em_aberto": str(t.saldo_em_aberto),
                "status": t.status,
            }
            for t in filtrados
        ],
    }


@beta_tool
def resumo_por_categoria(empresa: str = "") -> dict:
    """Agrupa os titulos por categoria de despesa, com total em aberto e total pago.

    Use quando o usuario perguntar "quanto devemos por tipo de despesa",
    "quais categorias tem mais gasto em aberto" ou similar.

    Args:
        empresa: Filtra por empresa. Vazio = consolidado de todas as empresas.
    """
    titulos = carregar_titulos()
    return {"empresa": empresa or "consolidado", "categorias": engine.resumo_por_categoria(titulos, empresa=empresa or None)}


@beta_tool
def detectar_atrasos(empresa: str = "") -> dict:
    """Lista titulos vencidos e nao pagos, com dias de atraso, ordenados do mais antigo.

    Use para responder sobre atrasos, pagamentos em aberto vencidos, ou
    quando o usuario pedir uma "visao de inadimplencia" com fornecedores.

    Args:
        empresa: Filtra por empresa. Vazio = todas.
    """
    titulos = carregar_titulos()
    hoje = data_referencia_atual()
    return {
        "data_referencia": hoje.isoformat(),
        "atrasos": engine.detectar_atrasos(titulos, hoje, empresa=empresa or None),
    }


@beta_tool
def comparar_periodos(periodo_1: str, periodo_2: str, empresa: str = "") -> dict:
    """Compara o total pago entre dois meses.

    Args:
        periodo_1: Primeiro mes no formato AAAA-MM (ex: "2026-08").
        periodo_2: Segundo mes no formato AAAA-MM (ex: "2026-09").
        empresa: Filtra por empresa. Vazio = consolidado.
    """
    titulos = carregar_titulos()
    return engine.comparar_periodos(titulos, periodo_1, periodo_2, empresa=empresa or None)


@beta_tool
def projetar_saldo(saldo_inicial: float, data_saldo: str, dias: int = 30, empresa: str = "") -> dict:
    """Projeta o saldo de caixa para os proximos dias, liquido das contas a pagar.

    Chame esta ferramenta quando o usuario anexar um extrato bancario e
    pedir uma projecao de saldo. Antes de chamar, extraia do extrato (nunca
    calcule) o saldo final e a data a que ele se refere - passe esses dois
    valores exatamente como aparecem no documento. Esta ferramenta faz a
    conta cruzando esse saldo com os titulos em aberto/parcial da base;
    ela NAO inclui entradas futuras (contas a receber), so as saidas ja
    registradas como contas a pagar.

    Args:
        saldo_inicial: Saldo extraido do extrato bancario anexado (numero, sem simbolo de moeda).
        data_saldo: Data a que o saldo do extrato se refere, formato AAAA-MM-DD.
        dias: Quantos dias projetar para frente a partir da data do saldo. Padrao 30.
        empresa: Filtra as obrigacoes por empresa. Vazio = consolidado de todas.
    """
    titulos = carregar_titulos()
    try:
        saldo = _decimal(saldo_inicial)
        data_ref = date.fromisoformat(data_saldo)
    except ValueError as exc:
        return {"erro": str(exc)}

    if dias < 1 or dias > 180:
        return {"erro": "dias deve estar entre 1 e 180."}

    return engine.projetar_saldo(titulos, saldo, data_ref, dias, empresa=empresa or None)


TOOLS = [
    get_indicador,
    listar_titulos,
    resumo_por_categoria,
    detectar_atrasos,
    comparar_periodos,
    projetar_saldo,
]
