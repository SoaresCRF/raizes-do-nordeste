from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body

from src.api.autenticacao import ClienteLogado
from src.api.dependencias import ConexaoBanco
from src.api.openapi import usuarios as documentacao
from src.api.schemas.usuarios import (
    ConsentimentoRegistrado,
    NovoCliente,
    NovoConsentimento,
    UsuarioCriado,
)
from src.application.usuarios import (
    anonimizar_conta,
    cadastrar_cliente,
    registrar_consentimento,
)

roteador = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@roteador.post("", status_code=HTTPStatus.CREATED, **documentacao.CADASTRAR_CLIENTE)
def cadastrar_novo_cliente(
    novo: Annotated[NovoCliente, Body(openapi_examples=documentacao.EXEMPLOS_CADASTRAR_CLIENTE)],
    conexao: ConexaoBanco,
) -> UsuarioCriado:
    cliente = cadastrar_cliente(
        conexao, novo.nome, novo.email, novo.senha, novo.consentimento_fidelidade
    )
    return UsuarioCriado.model_validate(cliente)


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
    return ConsentimentoRegistrado.model_validate(registro)


@roteador.delete("/me", status_code=HTTPStatus.NO_CONTENT, **documentacao.ANONIMIZAR_CONTA)
def anonimizar_minha_conta(cliente: ClienteLogado, conexao: ConexaoBanco) -> None:
    anonimizar_conta(conexao, cliente.id)
