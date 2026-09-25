# Agentes de IA Planning (pilotos)

Pilotos pequenos seguindo os moldes do AUREN Intelligence Ecosystem: a IA
nunca calcula números sozinha, indicadores/regras são fixos, e tudo passa
por ferramenta. Cada agente é um módulo independente em `src/`, com seu
próprio spec, dados fixture e serviço no `docker-compose.yml`.

| Agente | Módulo | Spec | Container |
|---|---|---|---|
| Contas a Pagar | `src/contas_a_pagar/` | `specs/contas-a-pagar/SPEC.md` | `agente-contas-a-pagar` |
| Conciliação Contábil | `src/contabilidade/` | `specs/conciliacao-contabil/SPEC.md` | `agente-contabil` |

## Agente de Contas a Pagar

- Responde perguntas sobre contas a pagar (total em aberto, vencido, a
  vencer, atrasos, resumo por categoria, comparação entre meses).
- Aceita um extrato bancário anexado (PDF, imagem ou CSV/TXT/OFX): extrai
  o saldo e a data do extrato, e projeta o saldo dos próximos dias líquido
  das obrigações já registradas na base.
- Fonte de dados hoje: `data/contas_a_pagar.csv` (dados fake). A leitura é
  isolada em `src/contas_a_pagar/datasource.py` para trocar pelo TOTVS RM
  depois sem mexer no agente nem nas ferramentas.

```bash
docker compose run --rm agente-contas-a-pagar
docker compose run --rm agente-contas-a-pagar "Qual o total em aberto?"
```

## Agente de Conciliação Contábil

**Somente leitura** — nenhuma ferramenta grava, altera ou apaga nada.
Registrar um lançamento de verdade é feito fora deste agente, pelo
sistema contábil real.

- Especialista em **razão, balancete, plano de contas e conferência de
  partidas dobradas**.
- Confere se um lançamento descrito em linguagem natural fecharia (débito
  == crédito, contas existentes) via `validar_lancamento` — isso é só uma
  conferência, não um registro; nada é gravado.
- Consulta o **razão** de qualquer conta (extrato cronológico com saldo
  acumulado) e gera o **balancete** (saldo de cada conta, com verificação
  se o total geral fecha).
- Fonte de dados hoje: `data/contabilidade/plano_de_contas.csv` e
  `data/contabilidade/lancamentos.csv` (10 lançamentos fake, fixos).
- Relatórios/gráficos e fechamento/reconciliação contra uma fonte externa
  (extrato bancário, subledger) ficam para a v2 — ver
  `specs/conciliacao-contabil/SPEC.md`.

```bash
docker compose run --rm agente-contabil
docker compose run --rm agente-contabil "Gere o balancete de setembro de 2026"
```

## Como rodar (qualquer um dos dois)

1. Copie `.env.example` para `.env` e coloque sua chave:

   ```bash
   cp .env.example .env
   # edite .env e defina ANTHROPIC_API_KEY=sk-ant-...
   ```

2. Suba o container do agente desejado:

   ```bash
   docker compose build
   docker compose run --rm agente-contas-a-pagar   # ou: agente-contabil
   ```

3. Converse (exemplos do agente contábil):

   ```
   voce> Quais contas de despesa existem?
   voce> Lance um pagamento de energia elétrica de R$ 1.200 via banco em 2026-09-23
   voce> Mostre o razão da conta de bancos
   voce> Gere o balancete de setembro de 2026
   ```

   Para anexar um arquivo, coloque-o em `./docs_enviados/` na sua máquina
   (é montado dentro do container no mesmo caminho) e use `/arquivo
   docs_enviados/nome-do-arquivo.pdf` antes do pedido.

4. Para um pedido único sem REPL (útil pra testar):

   ```bash
   docker compose run --rm agente-contabil "Gere o balancete geral"
   ```

## Rodar sem Docker (desenvolvimento)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

# Contas a pagar:
export CONTAS_A_PAGAR_DATA_REF=2026-09-21   # os dados fake foram desenhados para essa data
python -m src.contas_a_pagar.cli

# Conciliacao contabil:
python -m src.contabilidade.cli
```

## Testes

```bash
pip install pytest
python -m pytest tests/ -v
```

- `tests/test_contas_a_pagar_engine.py` valida os indicadores contra o CSV
  fixture de contas a pagar.
- `tests/test_contabilidade_engine.py` valida partida dobrada, saldo,
  razão e fechamento do balancete contra o CSV fixture contábil.

Nenhum teste chama a API da Claude — são testes do motor de cálculo
determinístico, o equivalente pequeno dos critérios de aceite do AUREN.

## Próximos passos (fora da v1)

**Contas a Pagar:**
- Trocar `src/contas_a_pagar/datasource.py` pela leitura real do TOTVS RM
  (falta definir o tipo de acesso e o mapeamento de tabelas/campos).
- Modo autônomo: rodar os indicadores periodicamente e gerar alertas.
- Deploy numa VPS pequena para o modo autônomo funcionar 24h.

**Conciliação Contábil:**
- Fechamento: comparar o razão contra uma fonte externa (extrato, ERP) e
  apontar divergências.
- DRE a partir do balancete; encerramento de exercício.
- Conexão com ERP real em vez do CSV fixture.
