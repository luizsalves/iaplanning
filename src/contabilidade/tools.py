"""Ferramentas expostas ao agente contabil. Toda leitura e escrita de dados
reais passa por aqui - o LLM nunca calcula saldo, razao ou balancete sozinho."""

from __future__ import annotations

from datetime import date

from anthropic import beta_tool

from . import engine
from .datasource import carregar_lancamentos, carregar_plano_de_contas, registrar_lancamento


@beta_tool
def consultar_plano_de_contas(tipo: str = "", busca: str = "") -> dict:
    """Lista as contas do plano de contas, opcionalmente filtradas.

    Use antes de lancar uma partida para confirmar o codigo exato da conta,
    ou quando o usuario perguntar quais contas existem.

    Args:
        tipo: Ativo, Passivo, Patrimonio Liquido, Receita ou Despesa. Vazio = todos os tipos.
        busca: Trecho do nome da conta (busca parcial, sem case). Vazio = todas.
    """
    plano = carregar_plano_de_contas()
    if tipo:
        plano = [c for c in plano if c.tipo.lower() == tipo.lower()]
    if busca:
        alvo = busca.lower()
        plano = [c for c in plano if alvo in c.nome.lower()]
    return {
        "quantidade": len(plano),
        "contas": [{"codigo": c.codigo, "nome": c.nome, "tipo": c.tipo, "natureza": c.natureza} for c in plano],
    }


@beta_tool
def lancar_partida(data: str, historico: str, partidas: list[dict]) -> dict:
    """Registra um lancamento contabil em partidas dobradas.

    So registra se a soma dos debitos for igual a soma dos creditos e todas
    as contas existirem no plano de contas - caso contrario, nada e gravado
    e o motivo da rejeicao e retornado. Confirme os codigos de conta com
    `consultar_plano_de_contas` antes de chamar esta ferramenta se nao
    tiver certeza deles.

    Args:
        data: Data do lancamento, formato AAAA-MM-DD.
        historico: Descricao do fato contabil (ex: "Pagamento de aluguel via banco").
        partidas: Lista de partidas, cada uma um objeto com:
            conta (codigo exato do plano de contas, ex: "1.1.02"),
            tipo ("D" para debito ou "C" para credito),
            valor (numero positivo, sem simbolo de moeda).
            Precisa ter pelo menos duas partidas e a soma dos debitos tem
            que ser igual a soma dos creditos.
    """
    plano = carregar_plano_de_contas()

    try:
        data_lancamento = date.fromisoformat(data)
    except ValueError:
        return {"aceito": False, "motivo": f"Data invalida: {data!r}, use AAAA-MM-DD."}

    valido, motivo = engine.validar_partidas(plano, partidas)
    if not valido:
        return {"aceito": False, "motivo": motivo}

    lancamento_id = registrar_lancamento(data_lancamento, historico, partidas)
    return {
        "aceito": True,
        "lancamento_id": lancamento_id,
        "data": data_lancamento.isoformat(),
        "historico": historico,
        "partidas": partidas,
    }


@beta_tool
def consultar_razao(conta: str, data_inicio: str = "", data_fim: str = "") -> dict:
    """Retorna o razao (extrato) de uma conta: cada lancamento que a afetou,
    em ordem cronologica, com saldo acumulado apos cada partida.

    Args:
        conta: Codigo exato da conta no plano de contas (ex: "1.1.02").
        data_inicio: Filtra partidas a partir desta data (AAAA-MM-DD). Vazio = desde o inicio.
        data_fim: Filtra partidas ate esta data (AAAA-MM-DD). Vazio = ate a mais recente.
    """
    plano = carregar_plano_de_contas()
    conta_obj = engine.buscar_conta(plano, conta)
    if conta_obj is None:
        return {"erro": f"Conta {conta!r} nao existe no plano de contas."}

    di = date.fromisoformat(data_inicio) if data_inicio else None
    df = date.fromisoformat(data_fim) if data_fim else None

    partidas = carregar_lancamentos()
    extrato = engine.razao_da_conta(conta_obj, partidas, data_inicio=di, data_fim=df)

    return {
        "conta": {"codigo": conta_obj.codigo, "nome": conta_obj.nome, "natureza": conta_obj.natureza},
        "quantidade_movimentos": len(extrato),
        "movimentos": extrato,
    }


@beta_tool
def gerar_balancete(data_inicio: str = "", data_fim: str = "", tipo: str = "") -> dict:
    """Gera o balancete: total de debito, total de credito e saldo de cada
    conta movimentada no periodo, mais a verificacao se o balancete fecha
    (soma geral dos debitos == soma geral dos creditos).

    Args:
        data_inicio: Filtra o periodo a partir desta data (AAAA-MM-DD). Vazio = desde o inicio.
        data_fim: Filtra o periodo ate esta data (AAAA-MM-DD). Vazio = ate a mais recente.
        tipo: Ativo, Passivo, Patrimonio Liquido, Receita ou Despesa. Vazio = todos os tipos.
    """
    plano = carregar_plano_de_contas()
    partidas = carregar_lancamentos()

    di = date.fromisoformat(data_inicio) if data_inicio else None
    df = date.fromisoformat(data_fim) if data_fim else None

    return engine.gerar_balancete(plano, partidas, data_inicio=di, data_fim=df, tipo=tipo or None)


TOOLS = [
    consultar_plano_de_contas,
    lancar_partida,
    consultar_razao,
    gerar_balancete,
]
