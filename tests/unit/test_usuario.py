import pytest

from src.domain.erros.erros import AcessoNegado, DadosInvalidos, DetalheErro
from src.domain.usuario.usuario import (
    PERFIS_LOTADOS_EM_UNIDADE,
    Perfil,
    UsuarioAutenticado,
    validar_lotacao,
    verificar_acesso_a_unidade,
)


@pytest.mark.parametrize("perfil", [Perfil.ATENDENTE, Perfil.COZINHA, Perfil.GERENTE])
def test_perfil_de_unidade_exige_unidade(perfil):
    with pytest.raises(DadosInvalidos) as erro:
        validar_lotacao(perfil, None)

    assert erro.value.detalhes == [DetalheErro("unidadeId", f"Obrigatório para o perfil {perfil}")]


def test_admin_nao_tem_unidade():
    with pytest.raises(DadosInvalidos) as erro:
        validar_lotacao(Perfil.ADMIN, 1)

    assert erro.value.detalhes == [DetalheErro("unidadeId", "Não se aplica ao perfil ADMIN")]


def test_cliente_nao_e_perfil_de_funcionario():
    with pytest.raises(DadosInvalidos) as erro:
        validar_lotacao(Perfil.CLIENTE, None)

    assert erro.value.detalhes == [DetalheErro("perfil", "CLIENTE não é perfil de funcionário")]


@pytest.mark.parametrize(("perfil", "unidade_id"), [(Perfil.GERENTE, 1), (Perfil.ADMIN, None)])
def test_aceita_lotacao_coerente(perfil, unidade_id):
    validar_lotacao(perfil, unidade_id)


def _usuario(perfil: Perfil, unidade_id: int | None) -> UsuarioAutenticado:
    return UsuarioAutenticado(id=1, perfil=perfil, unidade_id=unidade_id, sessao_id=1)


@pytest.mark.parametrize("perfil", PERFIS_LOTADOS_EM_UNIDADE)
def test_funcionario_nao_atua_em_outra_unidade(perfil):
    with pytest.raises(AcessoNegado) as erro:
        verificar_acesso_a_unidade(_usuario(perfil, 1), 2)

    assert erro.value.mensagem == "Usuário sem acesso à unidade 2"


@pytest.mark.parametrize(
    ("perfil", "unidade_id"),
    [(Perfil.ATENDENTE, 1), (Perfil.COZINHA, 1), (Perfil.GERENTE, 1), (Perfil.ADMIN, None)],
)
def test_atua_na_unidade_permitida(perfil, unidade_id):
    verificar_acesso_a_unidade(_usuario(perfil, unidade_id), 1)


def test_cliente_nao_e_barrado_pela_regra_de_unidade():
    verificar_acesso_a_unidade(_usuario(Perfil.CLIENTE, None), 1)
