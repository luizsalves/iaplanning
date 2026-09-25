# Spec — Agente de Conciliação Contábil (piloto)

Versão do contrato: 1.1
Status: em implementação (v1)

## 1. Objetivo

Segundo piloto no mesmo molde do AUREN Intelligence Ecosystem (ver
`specs/contas-a-pagar/SPEC.md` para o primeiro): IA nunca calcula número
oficial sozinha, todo cálculo passa por ferramenta, e o agente é
especialista em um domínio focado — aqui, contabilidade societária básica.

Os dois pilotos (`contas-a-pagar` e `conciliacao-contabil`) coexistem no
mesmo repositório como agentes independentes (módulos separados em
`src/`, containers separados no `docker-compose.yml`).

**O agente é somente leitura.** Nenhuma ferramenta grava, altera ou apaga
dado nenhum — ele consulta, confere e produz relatórios a partir do que já
está na base. Registrar um lançamento de verdade é feito fora deste
agente, pelo sistema contábil da empresa.

## 2. Escopo da v1

Dentro:

- **Plano de contas** fixo (`data/contabilidade/plano_de_contas.csv`):
  código, nome, tipo (Ativo/Passivo/Patrimônio Líquido/Receita/Despesa) e
  natureza (Devedora/Credora).
- **Conferência de partidas dobradas**: o usuário descreve um lançamento
  (data, histórico, partidas) e o agente chama `validar_lancamento`, que
  confere se débito == crédito e se todas as contas existem — e devolve o
  resultado (fecha ou não, e por quê). Isso **não grava nada**; é só uma
  conferência para ajudar a montar um lançamento correto antes de
  registrá-lo no sistema contábil real.
- **Razão**: extrato de uma conta, em ordem cronológica, com saldo
  acumulado após cada lançamento já existente na base.
- **Balancete**: total de débito, crédito e saldo de cada conta
  movimentada num período, mais a verificação se o balancete fecha (soma
  geral dos débitos == soma geral dos créditos).
- Usuário pode anexar documentos (nota, extrato, planilha) como contexto
  para o agente entender um fato contábil e ajudar a conferir as partidas.
- Roda local, em container Docker (`agente-contabil` no `docker-compose.yml`).

Fora da v1 (próxima fase):

- **Relatórios e gráficos** de razão/balancete (ex.: evolução de saldo por
  conta, comparação entre períodos) — próximo passo imediato.
- **Fechamento / reconciliação contra fonte externa** (ex.: comparar o
  razão de uma conta com um extrato bancário ou um subledger e apontar
  divergências).
- Registro real de lançamentos — se algum dia entrar em escopo, é uma
  decisão à parte, com uma ferramenta de escrita explicitamente autorizada
  e revisada, não uma extensão implícita da conferência.
- Múltiplos períodos fiscais, encerramento de exercício, apuração de
  resultado (DRE a partir do balancete).
- Conexão com ERP real (TOTVS RM ou outro) — mesma pendência já registrada
  no piloto de contas a pagar.
- Multi-empresa / multi-tenant.

## 3. Regra central (herdada do AUREN)

```
LLM
= entende o pedido, escolhe a ferramenta, explica o resultado

Ferramentas (src/contabilidade/tools.py)
= unica porta de entrada para consultar dados reais - SOMENTE LEITURA

Motor de calculo (src/contabilidade/engine.py)
= valida partida dobrada (sem persistir), calcula saldo/razao/balancete - sempre com Decimal

Fonte de dados (src/contabilidade/datasource.py)
= CSVs fixture (plano de contas + lancamentos) - so leitura, nenhuma funcao de escrita
```

## 4. Critérios de aceite

- **AC-01 — Partida dobrada:** `validar_lancamento` responde `fecha: true`
  somente quando a soma dos débitos é exatamente igual à soma dos créditos
  (arredondamento em 2 casas decimais) e todas as contas existem — sem
  gravar nada em nenhum dos dois casos.
- **AC-02 — Conta válida:** `validar_lancamento` responde `fecha: false`
  com o motivo quando alguma partida referencia um código fora do plano
  de contas.
- **AC-03 — Natureza determina o efeito no saldo:** para conta Devedora,
  débito aumenta e crédito diminui o saldo; para conta Credora, o
  inverso. Testado em `tests/test_contabilidade_engine.py`.
- **AC-04 — Razão reconcilia com o saldo:** o saldo acumulado no último
  movimento do razão de uma conta é igual ao saldo calculado
  diretamente por `saldo_da_conta` para o mesmo período.
- **AC-05 — Balancete fecha:** a soma geral dos débitos de todas as
  contas tem que ser igual à soma geral dos créditos; se não fechar, é
  sinalizado explicitamente (`balancete_fecha: false`), nunca escondido.
- **AC-06 — Sem invenção:** se uma conta não existe ou uma data é
  inválida, a ferramenta retorna erro explícito — o agente nunca
  inventa um código de conta, um saldo ou um lançamento.
- **AC-07 — Sem escrita:** nenhuma ferramenta do agente tem efeito
  colateral sobre `data/contabilidade/*.csv` — confirmado por não existir
  nenhuma função de escrita em `src/contabilidade/datasource.py`.

## 5. Segurança (herdada do AUREN, escala reduzida)

- O agente é **somente leitura**: `src/contabilidade/datasource.py` não
  tem nenhuma função que escreva em disco. `validar_lancamento` é uma
  conferência determinística (via `engine.validar_partidas`), nunca uma
  gravação.
- Conteúdo de documentos anexados pelo usuário é tratado como dado, nunca
  como instrução (guardrail no system prompt do agente).
- Se no futuro fizer sentido dar ao agente uma ferramenta de escrita real
  (registrar um lançamento de fato), isso exige decisão explícita do
  responsável pelo produto — nunca é assumido por implementação.
