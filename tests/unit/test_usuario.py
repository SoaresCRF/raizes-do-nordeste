import pytest

from src.domain.erros.erros import DadosInvalidos, DetalheErro
from src.domain.usuario.usuario import Perfil, validar_lotacao


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
