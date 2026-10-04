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

## Banco de dados: migrations e seed

Com o banco rodando:

```bash
uv run python -m alembic upgrade head
uv run python -m src.infrastructure.database.seeds
```

O seed apaga todos os dados do banco `raizes` e recria os dados de desenvolvimento: as unidades Recife (id 1, cozinha completa) e Caruaru (id 2, formato reduzido), os produtos do estudo de caso com preços fictícios, o estoque de cada unidade e um usuário de cada perfil. Todos os usuários usam a senha `Raizes@2026`:

| Perfil | E-mail | Unidade |
|---|---|---|
| ADMIN | admin@raizesdonordeste.com.br | — |
| GERENTE | gerente.recife@raizesdonordeste.com.br | 1 |
| GERENTE | gerente.caruaru@raizesdonordeste.com.br | 2 |
| ATENDENTE | atendente.recife@raizesdonordeste.com.br | 1 |
| COZINHA | cozinha.recife@raizesdonordeste.com.br | 1 |
| CLIENTE (com consentimento de fidelidade) | cliente@raizesdonordeste.com.br | — |
| CLIENTE (sem consentimento) | cliente.sem.consentimento@raizesdonordeste.com.br | — |

Essas senhas existem só para desenvolvimento local.

## Executar a API

Com o banco no ar e as migrations aplicadas:

```bash
uv run python -m src.main
```

A API sobe em `http://127.0.0.1:<PORTA>`, com a porta definida no `.env` (8000 no exemplo). O Swagger fica em `/docs` e o contrato OpenAPI em `/docs/openapi.json`. Os logs saem no terminal em JSON, uma linha por evento, com o `request_id` de cada requisição.

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
