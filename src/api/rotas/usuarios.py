from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body, Depends

from src.api.autenticacao import ClienteLogado, UsuarioLogado, exigir_perfil
from src.api.dependencias import ConexaoBanco, ServicoHashSenha
from src.api.openapi import usuarios as documentacao
from src.api.schemas.usuarios import (
    ConsentimentoRegistrado,
    FuncionarioCriado,
    MinhaConta,
    NovoCliente,
    NovoConsentimento,
    NovoFuncionario,
    UsuarioCriado,
)
from src.application.usuarios.cadastro import cadastrar_cliente, cadastrar_funcionario
from src.application.usuarios.conta import (
    anonimizar_conta,
    consultar_conta,
    registrar_consentimento,
)
from src.domain.usuario.usuario import Perfil

roteador = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@roteador.post("", status_code=HTTPStatus.CREATED, **documentacao.CADASTRAR_CLIENTE)
def cadastrar_novo_cliente(
    novo: Annotated[NovoCliente, Body(openapi_examples=documentacao.EXEMPLOS_CADASTRAR_CLIENTE)],
    conexao: ConexaoBanco,
    hash_senha: ServicoHashSenha,
) -> UsuarioCriado:
    cliente = cadastrar_cliente(
        conexao, hash_senha, novo.nome, novo.email, novo.senha, novo.consentimento_fidelidade
    )
    return UsuarioCriado.model_validate(cliente, from_attributes=True)


@roteador.get("/me", **documentacao.MINHA_CONTA)
def consultar_minha_conta(usuario: UsuarioLogado, conexao: ConexaoBanco) -> MinhaConta:
    conta = consultar_conta(conexao, usuario.id)
    return MinhaConta(
        id=conta.usuario.id,
        nome=conta.usuario.nome,
        email=conta.usuario.email,
        perfil=conta.usuario.perfil,
        unidade_id=conta.usuario.unidade_id,
        consentimentos=[
            ConsentimentoRegistrado.model_validate(registro, from_attributes=True)
            for registro in conta.consentimentos
        ],
    )


@roteador.post(
    "/me/consentimentos", status_code=HTTPStatus.CREATED, **documentacao.REGISTRAR_CONSENTIMENTO
)
def registrar_meu_consentimento(
    novo: Annotated[
        NovoConsentimento,
        Body(openapi_examples=documentacao.EXEMPLOS_REGISTRAR_CONSENTIMENTO),
    ],
    cliente: ClienteLogado,
    conexao: ConexaoBanco,
) -> ConsentimentoRegistrado:
    registro = registrar_consentimento(
        conexao, cliente.id, novo.finalidade, novo.concedido, novo.versao_termo
    )
    return ConsentimentoRegistrado.model_validate(registro, from_attributes=True)


@roteador.delete("/me", status_code=HTTPStatus.NO_CONTENT, **documentacao.ANONIMIZAR_CONTA)
def anonimizar_minha_conta(
    cliente: ClienteLogado, conexao: ConexaoBanco, hash_senha: ServicoHashSenha
) -> None:
    anonimizar_conta(conexao, hash_senha, cliente.id)


@roteador.post(
    "/funcionarios",
    status_code=HTTPStatus.CREATED,
    dependencies=[Depends(exigir_perfil(Perfil.ADMIN))],
    **documentacao.CADASTRAR_FUNCIONARIO,
)
def cadastrar_novo_funcionario(
    novo: Annotated[
        NovoFuncionario, Body(openapi_examples=documentacao.EXEMPLOS_CADASTRAR_FUNCIONARIO)
    ],
    conexao: ConexaoBanco,
    hash_senha: ServicoHashSenha,
) -> FuncionarioCriado:
    funcionario = cadastrar_funcionario(
        conexao, hash_senha, novo.nome, novo.email, novo.senha, novo.perfil, novo.unidade_id
    )
    return FuncionarioCriado.model_validate(funcionario, from_attributes=True)
