# Spec — Agente de Contas a Pagar (piloto)

Versao do contrato: 1.0
Status: em implementacao (v1)

## 1. Objetivo

Provar, num projeto pequeno, o mesmo molde que o AUREN Intelligence
Ecosystem define para o IA Planning completo — IA nunca calcula numero
oficial sozinha, indicadores sao fixos, tudo passa por ferramenta — antes
de investir no ecossistema inteiro (Factory, multi-repo, multi-agente).

Baseado em `PREPARACAO_AGENTES_HARNESS.md` (secao 9, TASK-001), mas com
escopo reduzido para v1.

## 2. Escopo da v1

Dentro:

- Agente responde perguntas em linguagem natural sobre contas a pagar
  (modo prompt).
- Indicadores fixos: total em aberto, total vencido, a vencer hoje / 7
  dias, total pago no mes, resumo por categoria, lista de atrasos.
- Usuario pode anexar um extrato bancario (PDF, imagem ou texto/CSV/OFX);
  o agente extrai saldo final e data do extrato, e projeta o saldo dos
  proximos N dias liquido das obrigacoes ja registradas na base.
- Roda local, em um container Docker.
- Fonte de dados: CSV fixture (`data/contas_a_pagar.csv`).

Fora da v1 (proxima fase):

- Modo autonomo (o agente vigiando a base sozinho e alertando por conta
  propria) - fica para depois que o modo prompt estiver validado.
- Conexao real com TOTVS RM - a camada `src/datasource.py` ja isola essa
  troca; falta confirmar como sera o acesso de leitura (conexao direta,
  view/API, ou exportacao) e o mapeamento de tabelas/campos do RM.
- Deploy em VPS / disponibilidade 24h - roda local por enquanto.
- Contas a receber / entradas futuras - a projecao de saldo so conhece
  saidas (contas a pagar), por isso e conservadora.

## 3. Regra central (herdada do AUREN)

```
LLM
= le a pergunta, escolhe a ferramenta, explica o resultado

Ferramentas (src/tools.py)
= unica porta de entrada para dados reais

Motor de calculo (src/engine.py)
= faz a conta, sempre com Decimal, nunca com LLM

Fonte de dados (src/datasource.py)
= hoje CSV fixture, depois TOTVS RM - o resto do codigo nao muda
```

## 4. Criterios de aceite (adaptados de AC-01 a AC-12 do documento original)

- **AC-01 — Consulta:** para os filtros dados (empresa/fornecedor/categoria/status),
  `listar_titulos` retorna exatamente os titulos correspondentes, excluindo cancelados.
- **AC-02 — Valores:** os totais de `get_indicador` batem com o calculo manual
  sobre o fixture (ver `tests/test_engine.py`); nunca soma moedas diferentes
  sem conversao explicita (fora do escopo v1, so ha BRL).
- **AC-03 — Situacao:** `detectar_atrasos` so lista titulos com status
  aberto/parcial e vencimento anterior a data de referencia.
- **AC-05 — Ausencia ou falha:** se o indicador pedido nao existir, a
  ferramenta retorna erro explicito com a lista de indicadores validos -
  nunca inventa um numero.
- **AC-09 — Classificacao:** `resumo_por_categoria` reconcilia com o total
  geral (soma das categorias == total em aberto/pago do periodo).
- **AC-10 — Atrasos:** `detectar_atrasos` calcula dias de atraso comparando
  vencimento com a data de referencia explicita (nunca a data real do
  sistema sem avisar).
- **AC-11/AC-12 (adaptado) — Projecao de saldo a partir de extrato:** dado
  um saldo e uma data extraidos de um documento anexado, `projetar_saldo`
  reconcilia a saida acumulada com os titulos de origem, sinaliza
  separadamente obrigacoes ja vencidas na data do extrato, e deixa
  explicito que a projecao nao inclui entradas futuras.

## 5. Seguranca (herdada do AUREN, escala reduzida)

- Acesso somente leitura aos dados de contas a pagar.
- Conteudo de documentos anexados pelo usuario e tratado como dado, nunca
  como instrucao (guardrail no system prompt do agente).
- Nenhuma ferramenta escreve, cadastra ou paga titulos.
