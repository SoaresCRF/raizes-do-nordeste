DESCRICAO_API = (
    "API REST única da rede Raízes do Nordeste para todos os canais de venda "
    "(`APP`, `TOTEM`, `BALCAO`, `PICKUP`, `WEB`).\n\n"
    "**Autenticação:** `POST /auth/login` devolve o `accessToken`. Nas rotas com cadeado, "
    "envie `Authorization: Bearer <accessToken>` (botão **Authorize**). Sem token ou com "
    "token inválido: 401 `NAO_AUTENTICADO`. Perfil ou unidade sem permissão: 403 "
    "`ACESSO_NEGADO`.\n\n"
    "**Listagens:** `?page=1&limit=10` (`limit` até 100). A resposta traz `dados` e "
    "`paginacao` (`page`, `limit`, `total`, `totalPaginas`).\n\n"
    "**Erros:** todo erro segue o schema `RespostaErro`: `error`, `message`, `details[]` "
    "(`field`, `issue`), `timestamp`, `path` e `requestId`. Body que não é JSON: 400 "
    "`JSON_INVALIDO`. Campo ausente, tipo ou formato inválido e campo não previsto no body: "
    "422 `VALIDACAO_FALHOU`. Qualquer rota pode ainda responder 405 `METODO_NAO_PERMITIDO` "
    "e 500 `ERRO_INTERNO` (mensagem genérica; o detalhe fica só no log).\n\n"
    "**Formatos:** datas em ISO 8601 UTC (`2026-02-05T12:00:00Z`); valores em reais como "
    "número (`129.7`).\n\n"
    "**Pagamento:** o gateway é simulado e nenhum pagamento real acontece. O header "
    "`X-Simular-Resultado` escolhe o resultado do mock."
)

TAGS = [
    {"name": "Auth", "description": "Login e logout."},
    {
        "name": "Usuarios",
        "description": "Cadastro de clientes, consentimentos e anonimização da própria conta.",
    },
    {"name": "Unidades", "description": "Unidades da rede e o cardápio de cada uma."},
    {"name": "Produtos", "description": "Catálogo de produtos da rede."},
    {"name": "Estoque", "description": "Saldo e movimentações de estoque por unidade."},
    {
        "name": "Pedidos",
        "description": "Criação, consulta, ciclo de vida e cancelamento de pedidos.",
    },
    {"name": "Pagamentos", "description": "Pagamento do pedido pelo gateway simulado."},
    {"name": "Fidelidade", "description": "Saldo, histórico e resgate de pontos."},
    {
        "name": "Auditoria",
        "description": "Registros de ações sensíveis e de acesso a dados pessoais.",
    },
]
