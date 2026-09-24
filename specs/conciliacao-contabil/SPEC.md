# Spec — Agente de Conciliação Contábil (piloto)

Versão do contrato: 1.0
Status: em implementação (v1)

## 1. Objetivo

Segundo piloto no mesmo molde do AUREN Intelligence Ecosystem (ver
`specs/contas-a-pagar/SPEC.md` para o primeiro): IA nunca calcula número
oficial sozinha, todo cálculo passa por ferramenta, e o agente é
especialista em um domínio focado — aqui, contabilidade societária básica.

Os dois pilotos (`contas-a-pagar` e `conciliacao-contabil`) coexistem no
mesmo repositório como agentes independentes (módulos separados em
`src/`, containers separados no `docker-compose.yml`).

## 2. Escopo da v1

Dentro:

- **Plano de contas** fixo (`data/contabilidade/plano_de_contas.csv`):
  código, nome, tipo (Ativo/Passivo/Patrimônio Líquido/Receita/Despesa) e
  natureza (Devedora/Credora).
- **Lançamento de partidas dobradas**: o agente recebe um pedido em
  linguagem natural, monta as partidas (conta, tipo D/C, valor) e chama
  `lancar_partida`, que só grava se débito == crédito e todas as contas
  existirem — senão rejeita e explica o motivo.
- **Razão**: extrato de uma conta, em ordem cronológica, com saldo
  acumulado após cada lançamento.
- **Balancete**: total de débito, crédito e saldo de cada conta
  movimentada num período, mais a verificação se o balancete fecha (soma
  geral dos débitos == soma geral dos créditos).
- Usuário pode anexar documentos (nota, extrato, planilha) como contexto
  para o agente decidir as partidas de um lançamento.
- Roda local, em container Docker (`agente-contabil` no `docker-compose.yml`).

Fora da v1 (próxima fase):

- **Fechamento / reconciliação contra fonte externa** (ex.: comparar o
  razão de uma conta com um extrato bancário ou um subledger e apontar
  divergências) — é o próximo passo natural depois que lançamento/razão/
  balancete estiverem validados.
- Múltiplos períodos fiscais, encerramento de exercício, apuração de
  resultado (DRE a partir do balancete).
- Conexão com ERP real (TOTVS RM ou outro) — mesma pendência já registrada
  no piloto de contas a pagar.
- Multi-empresa / multi-tenant.

## 3. Regra central (herdada do AUREN)

```
LLM
= entende o pedido, monta as partidas, escolhe a ferramenta, explica o resultado

Ferramentas (src/contabilidade/tools.py)
= unica porta de entrada para consultar E gravar dados reais

Motor de calculo (src/contabilidade/engine.py)
= valida partida dobrada, calcula saldo/razao/balancete - sempre com Decimal

Fonte de dados (src/contabilidade/datasource.py)
= hoje CSVs fixture (plano de contas + lancamentos); registrar_lancamento
  so acrescenta linhas, nunca reescreve o que ja existe
```

## 4. Critérios de aceite

- **AC-01 — Partida dobrada obrigatória:** `lancar_partida` só registra
  quando a soma dos débitos é exatamente igual à soma dos créditos
  (arredondamento em 2 casas decimais); caso contrário, nada é gravado.
- **AC-02 — Conta válida:** `lancar_partida` rejeita qualquer partida que
  referencie um código fora do plano de contas, sem gravar nada.
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

## 5. Segurança (herdada do AUREN, escala reduzida)

- `lancar_partida` é a única ferramenta de escrita, e só grava depois de
  validação determinística (não é o LLM decidindo se pode gravar).
- Conteúdo de documentos anexados pelo usuário é tratado como dado, nunca
  como instrução (guardrail no system prompt do agente).
- Nenhuma ferramenta edita ou apaga lançamentos já gravados — só
  acrescenta (append-only), preservando o histórico contábil.
