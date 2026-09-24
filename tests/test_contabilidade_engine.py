"""Testes do motor contabil contra o fixture data/contabilidade/*.csv.

Os 10 lancamentos fixture (LC-0001 a LC-0010) foram conferidos a mao -
ver o comentario de cada teste para a conta.
"""

from datetime import date
from decimal import Decimal

import pytest

from src.contabilidade import engine
from src.contabilidade.datasource import carregar_lancamentos, carregar_plano_de_contas


@pytest.fixture
def plano():
    return carregar_plano_de_contas()


@pytest.fixture
def lancamentos():
    return carregar_lancamentos()


def _conta(plano, codigo):
    conta = engine.buscar_conta(plano, codigo)
    assert conta is not None, f"conta {codigo} deveria existir no plano fixture"
    return conta


# --- validar_partidas ---------------------------------------------------


def test_validar_partidas_aceita_lancamento_balanceado(plano):
    valido, motivo = engine.validar_partidas(
        plano,
        [{"conta": "1.1.01", "tipo": "D", "valor": "500.00"}, {"conta": "4.1.01", "tipo": "C", "valor": "500.00"}],
    )
    assert valido is True
    assert motivo is None


def test_validar_partidas_rejeita_lancamento_desbalanceado(plano):
    valido, motivo = engine.validar_partidas(
        plano,
        [{"conta": "1.1.01", "tipo": "D", "valor": "500.00"}, {"conta": "4.1.01", "tipo": "C", "valor": "499.99"}],
    )
    assert valido is False
    assert "nao fecha" in motivo


def test_validar_partidas_rejeita_conta_inexistente(plano):
    valido, motivo = engine.validar_partidas(
        plano,
        [{"conta": "9.9.99", "tipo": "D", "valor": "10.00"}, {"conta": "4.1.01", "tipo": "C", "valor": "10.00"}],
    )
    assert valido is False
    assert "9.9.99" in motivo


def test_validar_partidas_rejeita_menos_de_duas_partidas(plano):
    valido, motivo = engine.validar_partidas(plano, [{"conta": "1.1.01", "tipo": "D", "valor": "10.00"}])
    assert valido is False


def test_validar_partidas_rejeita_valor_nao_positivo(plano):
    valido, motivo = engine.validar_partidas(
        plano,
        [{"conta": "1.1.01", "tipo": "D", "valor": "0"}, {"conta": "4.1.01", "tipo": "C", "valor": "0"}],
    )
    assert valido is False


# --- saldo / razao / balancete -------------------------------------------


def test_saldo_conta_devedora_bancos(plano, lancamentos):
    # Bancos (1.1.02): D 100000 (LC1) + 5000 (LC9) = 105000; C 12000+15000+4500 = 31500
    conta = _conta(plano, "1.1.02")
    resultado = engine.saldo_da_conta(conta, lancamentos)
    assert resultado["total_debito"] == Decimal("105000.00")
    assert resultado["total_credito"] == Decimal("31500.00")
    assert resultado["saldo"] == Decimal("73500.00")


def test_saldo_conta_credora_fornecedores(plano, lancamentos):
    # Fornecedores a pagar (2.1.01): C 25000 (LC2), D 12000 (LC5) -> saldo credor 13000
    conta = _conta(plano, "2.1.01")
    resultado = engine.saldo_da_conta(conta, lancamentos)
    assert resultado["saldo"] == Decimal("13000.00")


def test_razao_da_conta_bancos_mostra_saldo_acumulado(plano, lancamentos):
    conta = _conta(plano, "1.1.02")
    extrato = engine.razao_da_conta(conta, lancamentos)
    # Primeiro movimento: LC-0001, D 100000 -> saldo 100000
    assert extrato[0]["lancamento_id"] == "LC-0001"
    assert extrato[0]["saldo_apos"] == "100000.00"
    # Ultimo movimento (LC-0009, D 5000) fecha em 73500, batendo com saldo_da_conta
    assert extrato[-1]["saldo_apos"] == "73500.00"


def test_razao_da_conta_respeita_data_inicio(plano, lancamentos):
    conta = _conta(plano, "1.1.02")
    # A partir de 2026-09-10 (exclui LC-0001 e LC-0005, que sao antes)
    extrato = engine.razao_da_conta(conta, lancamentos, data_inicio=date(2026, 9, 10))
    ids = [m["lancamento_id"] for m in extrato]
    assert "LC-0001" not in ids
    assert "LC-0005" not in ids
    assert "LC-0007" in ids


def test_balancete_fecha_e_bate_total_geral(plano, lancamentos):
    balancete = engine.gerar_balancete(plano, lancamentos)
    assert balancete["balancete_fecha"] is True
    # Soma dos 10 lancamentos fixture (cada um contribui o mesmo valor em D e C).
    assert Decimal(balancete["total_geral_debito"]) == Decimal("200300.00")
    assert Decimal(balancete["total_geral_credito"]) == Decimal("200300.00")


def test_balancete_filtra_por_tipo(plano, lancamentos):
    balancete = engine.gerar_balancete(plano, lancamentos, tipo="Despesa")
    codigos = {linha["codigo"] for linha in balancete["contas"]}
    assert codigos == {"5.1.01", "5.2.01", "5.2.02", "5.2.04"}


def test_balancete_omite_conta_sem_movimento(plano, lancamentos):
    balancete = engine.gerar_balancete(plano, lancamentos)
    codigos = {linha["codigo"] for linha in balancete["contas"]}
    # 5.2.03 (Despesas Administrativas) nao tem nenhum lancamento no fixture.
    assert "5.2.03" not in codigos
