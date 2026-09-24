FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY specs/ specs/
COPY data/ data/

# Entrypoint padrao (contas a pagar); o docker-compose.yml sobrescreve
# `entrypoint` no servico agente-contabil para apontar para o outro CLI.
ENTRYPOINT ["python", "-m", "src.contas_a_pagar.cli"]
