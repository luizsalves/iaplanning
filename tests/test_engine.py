"""Testes do motor de calculo contra o fixture data/contas_a_pagar.csv.

Valores esperados foram conferidos a mao a partir do CSV, com data de
referencia fixa em 2026-09-21 (a mesma usada para desenhar o fixture).
"""

from datetime import date
from decimal import Decimal

import pytest

from src.datasource import carregar_titulos
from src import engine

DATA_REF = date(2026, 9, 21)


@pytest.fixture
def titulos():
    return carregar_titulos()


def test_cancelado_e_excluido_de_tudo(titulos):
    # AP-015 esta cancelado e nao pode aparecer em nenhum total.
    filtrados = engine.filtrar(titulos, fornecedor="Distribuidora Beta")
    ids = {t.id for t in filtrados}
    assert "AP-015" not in ids
    assert {"AP-003", "AP-004"}.issubset(ids)


def test_total_em_aberto_soma_saldo_nao_pago(titulos):
    # AP-003 (15200 aberto) + AP-004 (6400 aberto) + AP-005 (9800) + AP-006 (7200)
    # + AP-007 (22300) + AP-008 (5400) + AP-009 (4100) + AP-011 (2900-1450=1450)
    # + AP-012 (3800) + AP-014 (9900) + AP-016 (6700) + AP-017 (3300)
    total = engine.total_em_aberto(titulos)
    soma_manual = sum(
        Decimal(v)
        for v in [
            "15200.00", "6400.00", "9800.00", "7200.00", "22300.00",
            "5400.00", "4100.00", "1450.00", "3800.00", "9900.00",
            "6700.00", "3300.00",
        ]
    )
    assert total == soma_manual


def test_total_vencido_so_conta_status_aberto_parcial_no_passado(titulos):
    # Vencidos ate 2026-09-21: AP-003 (09-05), AP-004 (09-18), AP-011 (09-10, parcial),
    # AP-012 (09-12), AP-016 (09-01). AP-005/AP-006 vencem HOJE, nao sao "vencidos".
    total = engine.total_vencido(titulos, DATA_REF)
    esperado = Decimal("15200.00") + Decimal("6400.00") + Decimal("1450.00") + Decimal("3800.00") + Decimal("6700.00")
    assert total == esperado


def test_total_a_vencer_hoje(titulos):
    # AP-005 (9800) + AP-006 (7200) vencem em 2026-09-21.
    total = engine.total_a_vencer(titulos, DATA_REF, 0)
    assert total == Decimal("17000.00")


def test_detectar_atrasos_ordena_do_mais_antigo(titulos):
    atrasos = engine.detectar_atrasos(titulos, DATA_REF)
    ids = [a["id"] for a in atrasos]
    assert ids == ["AP-016", "AP-003", "AP-011", "AP-012", "AP-004"]
    assert atrasos[0]["dias_atraso"] == 20  # AP-016 venceu em 2026-09-01


def test_resumo_por_categoria_reconcilia_com_total_geral(titulos):
    resumo = engine.resumo_por_categoria(titulos)
    soma_categorias = sum(Decimal(c["total_em_aberto"]) for c in resumo)
    assert soma_categorias == engine.total_em_aberto(titulos)


def test_projetar_saldo_separa_vencidas_de_futuras(titulos):
    resultado = engine.projetar_saldo(titulos, Decimal("50000.00"), DATA_REF, dias=10)

    # "Vencidas nao pagas ate a data do saldo" usa <=: inclui tudo que ja
    # deveria ter saido do caixa na data do extrato, inclusive o que vence
    # exatamente nessa data (AP-005 e AP-006), alem dos vencidos de
    # test_total_vencido (AP-003, AP-004, AP-011, AP-012, AP-016).
    esperado_vencidas = (
        Decimal("15200.00") + Decimal("6400.00") + Decimal("1450.00") + Decimal("3800.00") + Decimal("6700.00")
        + Decimal("9800.00") + Decimal("7200.00")
    )
    assert Decimal(resultado["obrigacoes_vencidas_nao_pagas_ate_data_saldo"]) == esperado_vencidas

    # Dia 2026-09-22 (i=1): AP-017 (3300) vence.
    dia_1 = resultado["projecao_dias"][0]
    assert dia_1["data"] == "2026-09-22"
    assert Decimal(dia_1["saida_do_dia"]) == Decimal("3300.00")
    assert Decimal(dia_1["saldo_projetado"]) == Decimal("50000.00") - Decimal("3300.00")


def test_get_indicador_erro_para_nome_desconhecido():
    from src.tools import get_indicador, INDICADORES_DISPONIVEIS

    resultado = get_indicador(nome="nao_existe")
    assert "erro" in resultado
    assert set(resultado["indicadores_disponiveis"]) == set(INDICADORES_DISPONIVEIS)
