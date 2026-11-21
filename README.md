# Raízes do Nordeste: API Back-end

API REST da rede de lanchonetes Raízes do Nordeste, desenvolvida como projeto da trilha Back-end da UNINTER. Atende os canais APP, TOTEM, BALCAO, PICKUP e WEB numa única API, com pedidos, pagamento simulado, estoque por unidade, fidelização com consentimento (LGPD) e auditoria de ações sensíveis.

O fluxo entregue completo é o Fluxo A do roteiro: criar pedido, validar itens e estoque, registrar o pagamento mock e atualizar o status do pedido.

Repositório: <https://github.com/SoaresCRF/raizes-do-nordeste>.

## Requisitos

- Python 3.14 e [uv](https://docs.astral.sh/uv/) 0.12 ou superior
- Docker com Docker Compose, que sobe o banco PostgreSQL 17 (não é preciso instalar o PostgreSQL)

Dependências da aplicação, instaladas pelo `uv sync` a partir do `pyproject.toml` e do `uv.lock`: FastAPI e Uvicorn (API), SQLAlchemy 2 e Alembic (ORM e migrations), psycopg 3 (driver do PostgreSQL), pydantic-settings (configuração), PyJWT (token), argon2-cffi (hash de senha) e email-validator. Para desenvolvimento: ruff.

## Ambiente local

1. Copie o arquivo de exemplo e troque as senhas e o `JWT_SEGREDO`:

   ```bash
   cp .env.example .env
   ```

2. Instale as dependências:

   ```bash
   uv sync
   ```

3. Suba o PostgreSQL (cria o banco `raizes` e o usuário da aplicação na primeira execução):

   ```bash
   docker compose up -d --wait banco
   ```

   As senhas do banco só são aplicadas na primeira subida. Para recriar o banco do zero depois de mudar o `.env`: `docker compose down -v`.

## Variáveis de ambiente

O `.env` é lido pela API e pelo `docker compose`. Se alguma variável que a API usa estiver ausente ou inválida, a API não sobe e lista as variáveis com problema.

| Variável | Uso | Valor no exemplo |
|---|---|---|
| `PORTA` | Porta HTTP da API (1 a 65535) | `8000` |
| `NIVEL_LOG` | Nível mínimo dos logs: `DEBUG`, `INFO`, `WARNING` ou `ERROR` | `INFO` |
| `BANCO_ADMIN_SENHA` | Senha do superusuário `postgres` do container; só o `docker compose` usa | `troque-senha-admin` |
| `BANCO_APP_USUARIO` | Usuário com que a aplicação acessa o banco, criado na primeira subida do container | `raizes_app` |
| `BANCO_APP_SENHA` | Senha desse usuário | `troque-senha-app` |
| `BANCO_URL` | URL de conexão da API com o banco `raizes`; usuário e senha precisam ser os dois de cima | `postgresql+psycopg://raizes_app:...@127.0.0.1:5432/raizes` |
| `JWT_SEGREDO` | Chave que assina o access token; pelo menos 32 caracteres. Gere com `python -c "import secrets; print(secrets.token_urlsafe(48))"` | troque pelo gerado |
| `JWT_EXPIRACAO_MINUTOS` | Validade do access token, em minutos | `60` |

Use `127.0.0.1`, e não `localhost`, nas URLs do banco: o container publica a porta só em IPv4.

## Banco de dados: migrations e seed

Com o banco rodando:

```bash
uv run python -m alembic upgrade head
uv run python -m src.infrastructure.database.seeds
```

O seed apaga todos os dados do banco `raizes` e recria os dados de desenvolvimento: as unidades Recife (id 1, cozinha completa) e Caruaru (id 2, formato reduzido), os produtos do estudo de caso com preços fictícios, o estoque de cada unidade e ao menos um usuário de cada perfil. Todos os usuários usam a senha `Raizes@2026`:

| Perfil | E-mail | Unidade |
|---|---|---|
| ADMIN | admin@raizesdonordeste.com.br | — |
| GERENTE | gerente.recife@raizesdonordeste.com.br | 1 |
| ATENDENTE | atendente.recife@raizesdonordeste.com.br | 1 |
| COZINHA | cozinha.recife@raizesdonordeste.com.br | 1 |
| CLIENTE (com consentimento de fidelidade) | cliente@raizesdonordeste.com.br | — |

Essas senhas existem só para desenvolvimento local.

## Executar a API

Com o banco no ar e as migrations aplicadas:

```bash
uv run python -m src.main
```

A API sobe em `http://127.0.0.1:<PORTA>`, com a porta definida no `.env` (8000 no exemplo).

## Documentação da API

Com a API no ar, o Swagger fica em <http://127.0.0.1:8000/docs> e o contrato OpenAPI 3.1 em <http://127.0.0.1:8000/docs/openapi.json> (troque o 8000 se mudou a `PORTA` no `.env`). No Swagger, para chamar uma rota protegida, faça o `POST /auth/login`, copie o `accessToken` e cole-o no botão **Authorize**.

O mesmo contrato fica versionado em [`docs/openapi.json`](docs/openapi.json), legível sem subir a API.

## Diagramas

Os diagramas ficam em [`docs/diagramas/`](docs/diagramas/), cada um com a fonte Mermaid (`.mmd`) e a imagem gerada (`.png`):

- [DER](docs/diagramas/der.png): tabelas, colunas, chaves e restrições, com os nomes do banco. As principais tabelas e relacionamentos:
  - `pedido` pertence a uma `unidade` e, quando há cliente identificado, a um `usuario`; tem vários `item_pedido` (cada um aponta para um `produto`) e os registros de `pagamento`.
  - `estoque` guarda o saldo de um `produto` numa `unidade`; cada entrada ou saída vira uma `movimentacao_estoque`, ligada ao pedido quando é ele que movimenta o estoque.
  - `usuario` tem perfil e, para os perfis de loja, uma `unidade`; o cliente tem `consentimento` (LGPD) e `transacao_fidelidade` gerada pelos pedidos.
  - `log_auditoria` registra as ações sensíveis com o usuário e a unidade; `sessao` guarda as sessões de login de cada usuário, revogadas no logout.

## Testes

A coleção `postman/raizes-do-nordeste.postman_collection.json` tem uma requisição por cenário do plano de testes, nomeada `Txx – cenário`, e requisições `Prep – ...` que criam o estado de que um cenário precisa. De T01 a T14 estão os cenários que o roteiro exige; o T15 testa o filtro por `canalPedido`. As pastas seguem o fluxo: `Auth`, `Unidades`, `Pedidos`, `Pagamento`, `Status`, `Auditoria` e, por último, `Erros`, com os cenários negativos. O ambiente fica em `postman/raizes-do-nordeste.postman_environment.json`.

1. Recrie os dados com o seed (a coleção supõe o banco recém-semeado):

   ```bash
   uv run python -m alembic upgrade head
   uv run python -m src.infrastructure.database.seeds
   ```

2. Suba a API (`uv run python -m src.main`). Se a `PORTA` do `.env` não for 8000, ajuste a variável `baseUrl` do ambiente.
3. No Postman, importe a coleção e o ambiente, selecione o ambiente "Raízes do Nordeste — local" e rode a coleção inteira pelo Runner, na ordem em que está. Pela linha de comando, com Node.js instalado:

   ```bash
   npx --yes newman@6.2.1 run postman/raizes-do-nordeste.postman_collection.json \
     -e postman/raizes-do-nordeste.postman_environment.json
   ```

Não é preciso copiar token: as requisições de login guardam o token de cada perfil no ambiente, onde também ficam os ids criados no caminho. Para rodar de novo, rode o seed antes.
