import pytest

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.main import criar_app

ID_QUALQUER = "1"
EMAIL_POR_PERFIL = {
    "CLIENTE": f"cliente@{DOMINIO_EMAIL}",
    "ATENDENTE": f"atendente.recife@{DOMINIO_EMAIL}",
    "COZINHA": f"cozinha.recife@{DOMINIO_EMAIL}",
    "GERENTE": f"gerente.recife@{DOMINIO_EMAIL}",
    "ADMIN": f"admin@{DOMINIO_EMAIL}",
}
TODOS = frozenset(EMAIL_POR_PERFIL)
CLIENTE = frozenset({"CLIENTE"})
ADMIN = frozenset({"ADMIN"})
GESTORES = frozenset({"GERENTE", "ADMIN"})
FUNCIONARIOS = frozenset({"ATENDENTE", "COZINHA", "GERENTE", "ADMIN"})

ROTAS_PUBLICAS = {
    ("POST", "/auth/login"),
    ("POST", "/auth/refresh"),
    ("POST", "/usuarios"),
    ("GET", "/unidades"),
    ("GET", "/unidades/{id}"),
    ("GET", "/unidades/{id}/cardapio"),
    ("GET", "/produtos"),
    ("GET", "/produtos/{id}"),
}

# Matriz da seção 3 do PROJETO.md no nível da rota. Dono do recurso e unidade do
# funcionário (RN22, RN23) são conferidos nos testes de cada módulo.
PERFIS_POR_ROTA = {
    ("POST", "/auth/logout"): TODOS,
    ("GET", "/usuarios/me"): TODOS,
    ("POST", "/usuarios/me/consentimentos"): CLIENTE,
    ("DELETE", "/usuarios/me"): CLIENTE,
    ("POST", "/usuarios/funcionarios"): ADMIN,
    ("POST", "/unidades"): ADMIN,
    ("PUT", "/unidades/{id}"): ADMIN,
    ("POST", "/produtos"): ADMIN,
    ("PUT", "/produtos/{id}"): ADMIN,
    ("DELETE", "/produtos/{id}"): ADMIN,
    ("GET", "/estoque"): FUNCIONARIOS,
    ("POST", "/estoque/movimentacoes"): GESTORES,
    ("GET", "/estoque/movimentacoes"): GESTORES,
    ("POST", "/pedidos"): frozenset({"CLIENTE", "ATENDENTE"}),
    ("GET", "/pedidos"): TODOS,
    ("GET", "/pedidos/{id}"): TODOS,
    ("PATCH", "/pedidos/{id}/status"): FUNCIONARIOS,
    ("POST", "/pedidos/{id}/cancelamento"): frozenset({"CLIENTE", "ATENDENTE", "GERENTE", "ADMIN"}),
    ("POST", "/pagamentos"): frozenset({"CLIENTE", "ATENDENTE"}),
    ("GET", "/pagamentos/{id}"): frozenset({"CLIENTE", "ATENDENTE", "GERENTE", "ADMIN"}),
    ("GET", "/fidelidade/saldo"): CLIENTE,
    ("GET", "/fidelidade/historico"): CLIENTE,
    ("POST", "/fidelidade/resgates"): CLIENTE,
    ("GET", "/auditoria"): GESTORES,
    ("GET", "/relatorios/vendas"): GESTORES,
}

ACESSOS_NEGADOS = sorted(
    (metodo, caminho, perfil)
    for (metodo, caminho), permitidos in PERFIS_POR_ROTA.items()
    for perfil in TODOS - permitidos
)


def _url(caminho: str) -> str:
    return caminho.replace("{id}", ID_QUALQUER)


def test_toda_rota_esta_classificada_como_publica_ou_protegida(configuracao_api):
    app = criar_app(configuracao_api)

    # O FastAPI atual encapsula os routers incluídos, então app.routes não lista as rotas finais.
    rotas = {
        (metodo.upper(), caminho)
        for caminho, operacoes in app.openapi()["paths"].items()
        for metodo in operacoes
    }

    assert rotas == ROTAS_PUBLICAS | set(PERFIS_POR_ROTA)


@pytest.mark.parametrize(("metodo", "caminho"), sorted(PERFIS_POR_ROTA))
def test_rota_protegida_sem_token_devolve_401(cliente_http, metodo, caminho):
    resposta = cliente_http.request(metodo, _url(caminho))

    assert resposta.status_code == 401, resposta.text
    assert resposta.json()["error"] == "NAO_AUTENTICADO"


@pytest.mark.parametrize(("metodo", "caminho", "perfil"), ACESSOS_NEGADOS)
def test_perfil_fora_da_matriz_recebe_403(cliente_http, entrar, metodo, caminho, perfil):
    resposta = cliente_http.request(metodo, _url(caminho), headers=entrar(EMAIL_POR_PERFIL[perfil]))

    assert resposta.status_code == 403, resposta.text
    assert resposta.json()["error"] == "ACESSO_NEGADO"
