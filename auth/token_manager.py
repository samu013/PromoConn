import os

import requests
from dotenv import load_dotenv

from database.mercadolivre_tokens import (
    buscar_tokens,
    salvar_tokens,
)


load_dotenv()


TOKEN_URL = (
    "https://api.mercadolibre.com/"
    "oauth/token"
)

CLIENT_ID_ENV = "ML_CLIENT_ID"
CLIENT_SECRET_ENV = "ML_CLIENT_SECRET"
REFRESH_TOKEN_ENV = "ML_REFRESH_TOKEN"


# =========================================================
# VARIÁVEIS DE AMBIENTE
# =========================================================

def _variavel_obrigatoria(
    nome
):
    valor = os.getenv(
        nome,
        "",
    ).strip()

    if not valor:
        raise RuntimeError(
            f"A variável de ambiente "
            f"{nome} não está configurada."
        )

    return valor


# =========================================================
# REFRESH TOKEN
# =========================================================

def obter_refresh_token():
    """
    Prioridade:

    1. refresh_token salvo no Neon;
    2. ML_REFRESH_TOKEN do Render.

    A variável do Render serve como bootstrap.
    Depois disso, o Neon guarda os tokens novos.
    """

    tokens = buscar_tokens()

    if tokens:
        refresh_token = str(
            tokens.get(
                "refresh_token",
                "",
            )
        ).strip()

        if refresh_token:
            print(
                "🔐 Refresh token carregado "
                "do Neon."
            )

            return refresh_token

    refresh_token = (
        _variavel_obrigatoria(
            REFRESH_TOKEN_ENV
        )
    )

    print(
        "🔐 Refresh token carregado "
        "da variável de ambiente."
    )

    return refresh_token


# =========================================================
# RENOVAÇÃO
# =========================================================

def renovar_access_token(
    refresh_token=None,
):
    client_id = (
        _variavel_obrigatoria(
            CLIENT_ID_ENV
        )
    )

    client_secret = (
        _variavel_obrigatoria(
            CLIENT_SECRET_ENV
        )
    )

    if refresh_token is None:
        refresh_token = (
            obter_refresh_token()
        )

    refresh_token = str(
        refresh_token
        or ""
    ).strip()

    if not refresh_token:
        raise RuntimeError(
            "Refresh token do Mercado Livre "
            "não encontrado."
        )

    payload = {
        "grant_type":
            "refresh_token",

        "client_id":
            client_id,

        "client_secret":
            client_secret,

        "refresh_token":
            refresh_token,
    }

    print(
        "♻️ Renovando access token "
        "do Mercado Livre..."
    )

    try:
        resposta = requests.post(
            TOKEN_URL,

            # Endpoint OAuth recebe
            # os dados como formulário.
            data=payload,

            timeout=30,
        )

    except requests.RequestException as erro:
        raise RuntimeError(
            "Falha de rede ao renovar "
            "o token do Mercado Livre: "
            f"{erro}"
        ) from erro

    # =====================================================
    # ERRO
    # =====================================================

    if resposta.status_code != 200:
        raise RuntimeError(
            "Não foi possível renovar "
            "o token do Mercado Livre "
            f"(HTTP {resposta.status_code}): "
            f"{resposta.text}"
        )

    # =====================================================
    # RESPOSTA JSON
    # =====================================================

    try:
        dados = resposta.json()

    except ValueError as erro:
        raise RuntimeError(
            "O Mercado Livre retornou "
            "uma resposta inválida "
            "ao renovar o token."
        ) from erro

    novo_access_token = str(
        dados.get(
            "access_token",
            "",
        )
    ).strip()

    # O Mercado Livre pode devolver um
    # refresh token novo.
    #
    # Se isso acontecer, precisamos salvar
    # o novo imediatamente.
    novo_refresh_token = str(
        dados.get(
            "refresh_token",
            refresh_token,
        )
    ).strip()

    expires_in = dados.get(
        "expires_in"
    )

    if not novo_access_token:
        raise RuntimeError(
            "A renovação do Mercado Livre "
            "não retornou access_token."
        )

    if not novo_refresh_token:
        raise RuntimeError(
            "A renovação do Mercado Livre "
            "não retornou refresh_token válido."
        )

    # =====================================================
    # SALVA NO NEON
    # =====================================================

    salvar_tokens(
        access_token=
            novo_access_token,

        refresh_token=
            novo_refresh_token,

        expires_in=
            expires_in,
    )

    print(
        "✅ Token do Mercado Livre "
        "renovado com sucesso."
    )

    print(
        "✅ Novos tokens salvos no Neon."
    )

    return {
        **dados,

        "access_token":
            novo_access_token,

        "refresh_token":
            novo_refresh_token,
    }


# =========================================================
# EXECUÇÃO MANUAL
# =========================================================

if __name__ == "__main__":

    try:
        resultado = (
            renovar_access_token()
        )

        print()
        print(
            "✅ Renovação concluída."
        )

        print(
            "expires_in:",
            resultado.get(
                "expires_in"
            ),
        )

    except Exception as erro:
        print()
        print(
            "❌ Erro ao renovar token:"
        )

        print(
            erro
        )