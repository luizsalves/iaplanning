# Agente de Contas a Pagar (piloto)

Piloto pequeno seguindo os moldes do AUREN Intelligence Ecosystem (ver
`specs/contas-a-pagar/SPEC.md`): a IA nunca calcula números sozinha,
indicadores são fixos, e tudo passa por ferramenta. v1 só responde
perguntas via prompt — sem modo autônomo ainda.

## O que ele faz

- Responde perguntas sobre contas a pagar (total em aberto, vencido, a
  vencer, atrasos, resumo por categoria, comparação entre meses).
- Aceita um extrato bancário anexado (PDF, imagem ou CSV/TXT/OFX): extrai
  o saldo e a data do extrato, e projeta o saldo dos próximos dias líquido
  das obrigações já registradas na base.
- Roda local, num container Docker.

Fonte de dados hoje: `data/contas_a_pagar.csv` (dados fake). O código já
separa a leitura de dados (`src/datasource.py`) do resto, para trocar pelo
TOTVS RM depois sem mexer no agente nem nas ferramentas.

## Como rodar

1. Copie `.env.example` para `.env` e coloque sua chave:

   ```bash
   cp .env.example .env
   # edite .env e defina ANTHROPIC_API_KEY=sk-ant-...
   ```

2. Suba o container:

   ```bash
   docker compose build
   docker compose run --rm agente-contas-a-pagar
   ```

3. Converse:

   ```
   voce> Qual o total vencido hoje?
   voce> Quais categorias têm mais gasto em aberto?
   voce> /arquivo docs_enviados/extrato.pdf
   voce> Projete meu saldo para os próximos 30 dias
   ```

   Para anexar um arquivo, coloque-o em `./docs_enviados/` na sua máquina
   (é montado dentro do container no mesmo caminho) e use `/arquivo
   docs_enviados/nome-do-arquivo.pdf` antes da pergunta.

4. Para uma pergunta única sem REPL (útil pra testar):

   ```bash
   docker compose run --rm agente-contas-a-pagar "Qual o total em aberto?"
   ```

## Rodar sem Docker (desenvolvimento)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
export CONTAS_A_PAGAR_DATA_REF=2026-09-21   # os dados fake foram desenhados para essa data
python -m src.cli
```

## Testes

```bash
pip install pytest
python -m pytest tests/ -v
```

Os testes validam os indicadores contra o CSV fixture (sem chamar a API) —
é o equivalente pequeno dos critérios de aceite do AUREN (AC-01 a AC-12).

## Próximos passos (fora da v1)

- Trocar `src/datasource.py` pela leitura real do TOTVS RM (falta definir
  o tipo de acesso e o mapeamento de tabelas/campos).
- Modo autônomo: rodar os indicadores periodicamente e gerar alertas
  quando uma regra fixa disparar (atraso, variação de juros etc.).
- Deploy numa VPS pequena para o modo autônomo funcionar 24h.
