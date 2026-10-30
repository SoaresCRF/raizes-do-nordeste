from collections.abc import Mapping, Sequence
from typing import Any

from src.api.erros import DetalheResposta

ORIGENS_DE_PARAMETRO = {"body", "query", "path", "header", "cookie"}
PROBLEMA_GENERICO = "Valor inválido"
MENSAGEM_INTEIRO = "Deve ser um número inteiro"
MENSAGEM_DECIMAL = "Deve ser um número decimal"
MENSAGEM_BOOLEANO = "Deve ser true ou false"
MENSAGEM_OBJETO = "Deve ser um objeto JSON"

PROBLEMAS_POR_TIPO = {
    "missing": "Campo obrigatório",
    "extra_forbidden": "Campo não permitido",
    "int_parsing": MENSAGEM_INTEIRO,
    "int_type": MENSAGEM_INTEIRO,
    "int_from_float": MENSAGEM_INTEIRO,
    "decimal_parsing": MENSAGEM_DECIMAL,
    "decimal_type": MENSAGEM_DECIMAL,
    "decimal_max_places": "Deve ter no máximo {decimal_places} casas decimais",
    "decimal_max_digits": "Deve ter no máximo {max_digits} dígitos",
    "decimal_whole_digits": "Deve ter no máximo {whole_digits} dígitos antes da vírgula",
    "finite_number": "Deve ser um número finito",
    "bool_parsing": MENSAGEM_BOOLEANO,
    "bool_type": MENSAGEM_BOOLEANO,
    "string_type": "Deve ser um texto",
    "string_too_short": "Deve ter pelo menos {min_length} caractere(s)",
    "string_too_long": "Deve ter no máximo {max_length} caracteres",
    "greater_than": "Deve ser maior que {gt}",
    "greater_than_equal": "Deve ser maior ou igual a {ge}",
    "less_than": "Deve ser menor que {lt}",
    "less_than_equal": "Deve ser menor ou igual a {le}",
    "multiple_of": "Deve ser múltiplo de {multiple_of}",
    "enum": "Deve ser um destes valores: {expected}",
    "list_type": "Deve ser uma lista",
    "too_short": "Deve ter pelo menos {min_length} item(ns)",
    "model_attributes_type": MENSAGEM_OBJETO,
    "dict_type": MENSAGEM_OBJETO,
    "email_invalido": "Deve ser um e-mail válido",
    "uf_invalida": "Deve ser a sigla de uma UF do Brasil",
    "caractere_nulo": "Não pode conter o caractere nulo",
}


def _formatar_campo(localizacao: Sequence[str | int]) -> str:
    partes = localizacao
    if len(localizacao) > 1 and localizacao[0] in ORIGENS_DE_PARAMETRO:
        partes = localizacao[1:]
    campo = ""
    for parte in partes:
        if isinstance(parte, int):
            campo += f"[{parte}]"
        else:
            campo += f".{parte}" if campo else parte
    return campo


def _descrever_problema(erro: Mapping[str, Any]) -> str:
    modelo = PROBLEMAS_POR_TIPO.get(erro["type"])
    if modelo is None:
        return PROBLEMA_GENERICO
    contexto = dict(erro.get("ctx") or {})
    if "expected" in contexto:
        contexto["expected"] = contexto["expected"].replace(" or ", " ou ")
    return modelo.format(**contexto)


def detalhes_de_validacao(erros: Sequence[Mapping[str, Any]]) -> list[DetalheResposta]:
    return [
        DetalheResposta(field=_formatar_campo(erro["loc"]), issue=_descrever_problema(erro))
        for erro in erros
    ]
