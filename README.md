# Raízes do Nordeste — API Back-end

API REST da rede de lanchonetes Raízes do Nordeste, desenvolvida como projeto da trilha Back-end da UNINTER. Atende os canais APP, TOTEM, BALCAO, PICKUP e WEB numa única API, com pedidos, pagamento simulado, estoque por unidade, fidelização com consentimento (LGPD) e auditoria de ações sensíveis.

Stack: Python 3.14, FastAPI, SQLAlchemy 2 + Alembic, PostgreSQL 17 (Docker).

A especificação completa está em [PROJETO.md](PROJETO.md).
Repositório: <https://github.com/SoaresCRF/raizes-do-nordeste>.

## Requisitos

- Python 3.14 e [uv](https://docs.astral.sh/uv/) 0.12 ou superior
- Docker com Docker Compose

Dependências da aplicação, instaladas pelo `uv sync` a partir do `pyproject.toml` e do `uv.lock`: FastAPI e Uvicorn (API), SQLAlchemy 2 e Alembic (ORM e migrations), psycopg 3 (driver do PostgreSQL), pydantic-settings (configuração), PyJWT (token), argon2-cffi (hash de senha) e email-validator. Para desenvolvimento: pytest, httpx e ruff.

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

## Variáveis de ambiente

O `.env` é lido pela API e pelo `docker compose`. A API recusa subir, com a lista das variáveis problemáticas, se alguma das que ela usa estiver ausente ou inválida; `BANCO_URL_TESTE` é opcional para a API.

| Variável | Uso | Valor no exemplo |
|---|---|---|
| `PORTA` | Porta HTTP da API (1 a 65535) | `8000` |
| `NIVEL_LOG` | Nível mínimo dos logs: `DEBUG`, `INFO`, `WARNING` ou `ERROR` | `INFO` |
| `BANCO_ADMIN_SENHA` | Senha do superusuário `postgres` do container; só o `docker compose` usa | `troque-senha-admin` |
| `BANCO_APP_USUARIO` | Usuário com que a aplicação acessa o banco, criado na primeira subida do container | `raizes_app` |
| `BANCO_APP_SENHA` | Senha desse usuário | `troque-senha-app` |
| `BANCO_URL` | URL de conexão da API com o banco `raizes`; usuário e senha precisam ser os dois de cima | `postgresql+psycopg://raizes_app:...@127.0.0.1:5432/raizes` |
| `BANCO_URL_TESTE` | URL do banco `raizes_teste`, usado só pelos testes de integração | `postgresql+psycopg://raizes_app:...@127.0.0.1:5432/raizes_teste` |
| `JWT_SEGREDO` | Chave que assina o access token; pelo menos 32 caracteres. Gere com `python -c "import secrets; print(secrets.token_urlsafe(48))"` | troque pelo gerado |
| `JWT_EXPIRACAO_MINUTOS` | Validade do access token, em minutos (o refresh token vale 7 dias) | `60` |
| `GATEWAY_TIMEOUT_SEGUNDOS` | Tempo máximo de espera pelo gateway de pagamento simulado | `3` |

Use `127.0.0.1`, e não `localhost`, nas URLs do banco: o container publica a porta só em IPv4.

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

## Documentação da API

Com a API no ar, o Swagger fica em `http://127.0.0.1:<PORTA>/docs` e o contrato OpenAPI 3.1 em `http://127.0.0.1:<PORTA>/docs/openapi.json`. Cada rota traz o perfil autorizado, as regras que aplica, exemplos de request e de response e todos os status de erro, sempre no formato de erro padrão (`RespostaErro`). Para chamar uma rota protegida pela própria página, faça o `POST /auth/login`, copie o `accessToken` e cole-o no botão **Authorize**.

O mesmo contrato fica versionado em [`docs/openapi.json`](docs/openapi.json), legível sem subir a API. Depois de mudar uma rota ou um schema, gere o arquivo de novo, com o `.env` presente como na própria API (o teste `test_contrato_versionado_esta_igual_ao_da_api` falha enquanto ele estiver diferente do código):

```bash
uv run python -m src.api.openapi.exportar
```

Para validar o contrato contra a especificação OpenAPI, sem instalar nada no projeto:

```bash
uvx openapi-spec-validator==0.7.2 docs/openapi.json
```

## Diagramas

Os diagramas ficam em [`docs/diagramas/`](docs/diagramas/), cada um com a fonte Mermaid (`.mmd`) e a imagem gerada (`.png`):

- [DER](docs/diagramas/der.png): tabelas, colunas, chaves e restrições, com os nomes do banco.
- [Casos de uso](docs/diagramas/casos-de-uso.png): atores e casos de uso UC01–UC13; o Mermaid não tem notação própria de caso de uso, por isso atores são círculos e casos de uso, elipses.
- [Classes de domínio](docs/diagramas/classes.png): entidades de `src/domain/` com seus campos, enums e a interface do gateway de pagamento.
- [Arquitetura em camadas](docs/diagramas/arquitetura.png): API, Application, Domain e Infrastructure e o sentido das dependências.
- [Atividades do Fluxo A](docs/diagramas/atividades-fluxo-a.png): pedido → pagamento simulado → atualização de status, com os desvios de erro.
- [Sequência do Fluxo A](docs/diagramas/sequencia-fluxo-a.png): as mesmas etapas entre rotas, casos de uso, banco e gateway.

Depois de editar uma fonte, gere as imagens de novo (precisa do Node.js):

```bash
for fonte in docs/diagramas/*.mmd; do
  npx --yes @mermaid-js/mermaid-cli@11.17.0 -i "$fonte" -o "${fonte%.mmd}.png" -b white -s 2 -w 1600
done
```

## Lint e formatação

```bash
uv run ruff check .
uv run ruff format .
```

## Testes

### Testes automatizados

```bash
uv run python -m pytest
```

Os testes de integração precisam do banco rodando (passo 3 do ambiente local). As regras de domínio têm testes unitários em `tests/unit/` (estoque, pedido, fidelidade) e o fluxo pedido → pagamento → status é percorrido de ponta a ponta em `tests/integration/test_fluxo_a.py`. A quantidade inteira maior que zero da movimentação de estoque (RN06) e o resgate em múltiplos de 100 pontos (RN19) são validados no schema da API, na fronteira, e por isso estão nos testes de integração (`tests/integration/test_api_movimentacoes.py` e `tests/integration/test_api_resgates.py`).

### Coleção Postman

A coleção `postman/raizes-do-nordeste.postman_collection.json` tem uma requisição por cenário do plano de testes (T01 a T95), nomeada `Txx – cenário`, e requisições `Prep – ...` que criam o estado de que um cenário precisa. Os cenários negativos ficam na pasta `Erros`. O ambiente fica em `postman/raizes-do-nordeste.postman_environment.json`.

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

Não é preciso copiar token: as requisições de login guardam o token de cada perfil no ambiente, e os ids criados no caminho também ficam no ambiente. Para rodar de novo, rode o seed antes. O cenário T91 (produto sazonal fora do período) depende da janela da canjica junina no seed, de 1º de junho a 31 de julho de 2026.

### Plano de testes

São 95 cenários: 39 positivos e 56 negativos, dos quais 72 obrigatórios. A tabela completa, com ID, cenário, endpoint, pré-condição, entrada e resultado esperado, está na seção 11 do [PROJETO.md](PROJETO.md). A evidência de cada cenário é a requisição de mesmo ID na coleção, e o resultado da última execução completa está em [postman/resultado-execucao.txt](postman/resultado-execucao.txt).

Cobertura obrigatória do roteiro:

| Exigência | Requisições na coleção |
|---|---|
| Login com token válido | T01 |
| Acesso sem token (401) | T57 |
| Perfil sem permissão (403) | T36, T65 |
| Campo obrigatório ausente (422) | T51 |
| Tipo ou formato inválido | T09 (e-mail), T53 (quantidade negativa) |
| Pedido válido (201) | T50 |
| Produto ou unidade inexistente (404) | T54, T55 |
| Estoque insuficiente (409) | T56 |
| Pagamento aprovado atualiza o status | T68 |
| Pagamento recusado com status e mensagem coerentes | T69 |
| Ação sensível gera registro de auditoria | T82 |

## LGPD e privacidade

### Dados coletados

| Dado | Finalidade | Base legal (LGPD, art. 7º) | Observação |
|---|---|---|---|
| Nome, e-mail | Identificação, login, pedidos | Execução de contrato (V) | Obrigatórios no cadastro |
| Senha | Autenticação | Execução de contrato (V) | Só o hash argon2 é armazenado |
| Histórico de pedidos | Prestação do serviço, auditoria da franquia | Execução de contrato (V) e legítimo interesse (IX) | — |
| Pontos de fidelidade | Programa de fidelização | Consentimento (I) | Exige consentimento `FIDELIDADE` ativo |
| Logs de auditoria | Rastreabilidade e segurança | Legítimo interesse (IX) | Guardam só ids, nunca nome ou e-mail |

O cadastro de cliente recebe só nome, e-mail, senha e a escolha de participar da fidelidade; qualquer outro campo é recusado com 422. Data de nascimento e perfil para campanhas não são coletados.

### Consentimento

Cada concessão ou revogação (`POST /usuarios/me/consentimentos`) grava uma linha nova na tabela `consentimento`, com a finalidade, se foi concedido, a versão do termo aceita e a data em UTC. Nada é sobrescrito: o histórico completo fica guardado e vale o registro mais recente de cada finalidade. O cadastro já grava o primeiro registro a partir de `consentimentoFidelidade`. Sem consentimento `FIDELIDADE` vigente, o cliente não acumula nem resgata pontos; o saldo existente é mantido.

### Acesso a dados pessoais

Quando um funcionário consulta um pedido que identifica o cliente (`GET /pedidos/{id}`), a API grava na auditoria a ação `ACESSO_DADOS_PESSOAIS` com o id do funcionário, o id do cliente e o id do pedido, sem nome nem e-mail. Os logs da aplicação também não registram dados pessoais: o log de acesso guarda só o caminho (sem query string) e um erro de banco guarda só o tipo e o código SQLSTATE, porque a mensagem do Postgres pode repetir valores da linha.

### Retenção e anonimização

- Conta: o cliente pode pedir a anonimização a qualquer momento (`DELETE /usuarios/me`). Na hora, o nome vira "Cliente anonimizado", o e-mail vira `cliente-<id>@anonimizado.invalid`, a senha é trocada por um hash de um segredo descartado, a conta fica inativa e todas as sessões são revogadas.
- Pedidos, pagamentos, movimentações de estoque, consentimentos e auditoria continuam ligados ao id do cliente anonimizado, porque sustentam a contabilidade e a rastreabilidade da franquia.
- Prazo proposto: esses registros ficam guardados por 5 anos, o prazo de guarda de documentos fiscais e de prescrição do Código de Defesa do Consumidor, e depois podem ser descartados. A rotina automática de expurgo não faz parte deste MVP.

Todos os dados do seed e das evidências de teste são fictícios.

## Desempenho e escalabilidade

Os documentos do projeto não definem metas numéricas de carga. A arquitetura atende picos e crescimento assim:

- A API não guarda estado em memória entre requisições: o access token é JWT e as sessões de refresh ficam no banco. Mais instâncias podem rodar atrás de um balanceador sem afinidade de sessão.
- Toda listagem é paginada (`?page=1&limit=10`, máximo 100 por página).
- Os filtros mais usados têm índice: pedidos por unidade e status, por canal e por cliente; auditoria por entidade e id; movimentações por estoque.
- As listagens saem de uma consulta mais uma contagem, sem consultas em laço.
- A baixa de estoque e o pagamento travam a linha no banco (`SELECT ... FOR UPDATE`): dois pedidos simultâneos não vendem a mesma unidade e um pedido não é pago duas vezes.
- O gateway de pagamento tem timeout configurável (`GATEWAY_TIMEOUT_SEGUNDOS`); o mock simula o estouro do prazo com `X-Simular-Resultado: TIMEOUT`. Falha ou timeout do gateway geram o pagamento `ERRO` e a resposta 503, sem alterar o pedido.

## Regras documentadas e evolução

Regras que o estudo de caso pede e que ficam documentadas como proposta, sem implementação neste MVP.

### Promoções e campanhas (RF31)

Uma promoção tem período de vigência, as unidades e os produtos em que vale e um desconto em percentual ou em valor fixo. Ela entra no cálculo do total do pedido (RN08): depois de copiar o preço de cada item, a API aplica a promoção vigente do item e só então permite o resgate de pontos (RN19), que continua precisando ser menor que o total. Uma promoção por item, sem acumular. O desconto promocional fica num campo próprio do pedido, separado do desconto do resgate, e entra nos dados do `PEDIDO_CRIADO` na auditoria (RN20). Para implementar: tabela `promocao` (nome, tipo e valor do desconto, início e fim em UTC, ativa) ligada às unidades e aos produtos, cadastro restrito ao `ADMIN` e o cálculo no caso de uso de criar pedido.

### Campanhas segmentadas e descontos progressivos (RF32)

Evolução da fidelização: campanhas por frequência de compra, faixa etária ou perfil e descontos que crescem com o número de pedidos num período. Só valem para quem tem consentimento `MARKETING` vigente, finalidade que já existe e já é registrada por `POST /usuarios/me/consentimentos`. Segmentar por idade exige coletar a data de nascimento, que hoje fica fora do cadastro por minimização (RNF06); a coleta passaria a depender do mesmo consentimento.

### Variação de receitas por região (RF13)

Evolução do catálogo: o mesmo produto com receita, descrição ou preço próprios de uma região. Hoje o produto é único na rede e a unidade oferta o que tem registro de estoque (RN03). A variação viria de uma tabela `produto_regiao` (produto, região, descrição e preço) consultada pelo cardápio da unidade a partir de `unidade.regiao`; o preço regional seria copiado para o item no pedido, como o preço atual (RN08).

### Metas, indicadores e regras de funcionamento por unidade (RF35)

Evolução da gestão: metas de venda por unidade e período comparadas com o relatório de vendas (`GET /relatorios/vendas`, que já agrupa por unidade, região, canal e produto) e regras de funcionamento por unidade, como horário de atendimento e canais aceitos, guardadas numa tabela própria e conferidas na criação do pedido.

## Fora do escopo

O projeto roda só localmente e não vai ao ar. Num cenário de produção, ficariam como evolução:

- CORS com lista explícita das origens dos front-ends;
- limite de requisições (rate limiting) no login, no cadastro e na criação de pedidos;
- headers de segurança (`Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`) e HTTPS de ponta a ponta;
- deploy, monitoramento e o gateway de pagamento real no lugar do mock, com `Idempotency-Key` na solicitação de pagamento.
