# Raízes do Nordeste — API Back-end

API REST da rede de lanchonetes Raízes do Nordeste, desenvolvida como projeto da trilha Back-end da UNINTER. Atende os canais APP, TOTEM, BALCAO, PICKUP e WEB numa única API, com pedidos, pagamento simulado, estoque por unidade, fidelização com consentimento (LGPD) e auditoria de ações sensíveis.

Stack: Python 3.14, FastAPI, SQLAlchemy 2 + Alembic, PostgreSQL 17 (Docker).

A especificação completa está em [PROJETO.md](PROJETO.md).

## Requisitos

- Python 3.14 e [uv](https://docs.astral.sh/uv/) 0.12 ou superior
- Docker com Docker Compose

## Ambiente local

1. Copie o arquivo de exemplo e troque as senhas e o `JWT_SEGREDO`:

   ```bash
   cp .env.example .env
   ```

2. Instale as dependências:

   ```bash
   uv sync
   ```

3. Suba o PostgreSQL (cria os bancos `raizes` e `raizes_teste` e o usuário da aplicação na primeira execução):

   ```bash
   docker compose up -d --wait banco
   ```

   As senhas do banco só são aplicadas na primeira subida. Para recriar o banco do zero depois de mudar o `.env`: `docker compose down -v`.

## Lint e formatação

```bash
uv run ruff check .
uv run ruff format .
```

## Testes

```bash
uv run python -m pytest
```

Os testes de integração precisam do banco rodando (passo 3).

As instruções de migrations, seed e execução da API serão adicionadas conforme a implementação avança.
