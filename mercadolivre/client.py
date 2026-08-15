import json
import os
from pathlib import Path

import requests

from database.mercadolivre_tokens import (
    buscar_tokens,
    inicializar_tokens,
    token_expirado,
)


BASE_URL = (
    "https://api.mercadolibre.com"
)

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

TOKEN_FILE = (
    PROJECT_ROOT
    / "data"
    / "tokens.json"
)

ACCESS_TOKEN_ENV = (
    "MERCADO_LIVRE_ACCESS_TOKEN"
)

REFRESH_TOKEN_ENV = (
    "ML_REFRESH_TOKEN"
)


class MercadoLivreAuthenticationError(
    RuntimeError
):
    pass


class MercadoLivreClient:

    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self._auth_bloqueada = False

        self._carregar_tokens()

    # =====================================================
    # TOKENS
    # =====================================================

    def _tokens_do_arquivo(self):
        if not TOKEN_FILE.exists():
            return None

        try:
            with TOKEN_FILE.open(
                "r",
                encoding="utf-8",
            ) as arquivo:
                dados = json.load(
                    arquivo
                )

        except json.JSONDecodeError as erro:
            raise RuntimeError(
                "O arquivo de tokens não contém "
                f"JSON válido: {TOKEN_FILE}"
            ) from erro

        return dados

    def _carregar_tokens(self):
        """
        Fonte principal:
            Neon / mercadolivre_tokens.

        Bootstrap, apenas se a tabela estiver vazia:
            variáveis do Render ou tokens.json local.
        """

        tokens = buscar_tokens()

        if not tokens:
            access_ambiente = os.getenv(
                ACCESS_TOKEN_ENV,
                "",
            ).strip()

            refresh_ambiente = os.getenv(
                REFRESH_TOKEN_ENV,
                "",
            ).strip()

            dados_arquivo = (
                self._tokens_do_arquivo()
                or {}
            )

            access_inicial = (
                access_ambiente
                or str(
                    dados_arquivo.get(
                        "access_token",
                        "",
                    )
                ).strip()
            )

            refresh_inicial = (
                refresh_ambiente
                or str(
                    dados_arquivo.get(
                        "refresh_token",
                        "",
                    )
                ).strip()
            )

            tokens = inicializar_tokens(
                access_token=
                    access_inicial,

                refresh_token=
                    refresh_inicial,
            )

            if tokens:
                print(
                    "🔐 Tokens iniciais do "
                    "Mercado Livre salvos "
                    "no Neon."
                )

        if not tokens:
            raise RuntimeError(
                "Tokens do Mercado Livre não "
                "encontrados. Configure "
                "MERCADO_LIVRE_ACCESS_TOKEN e "
                "ML_REFRESH_TOKEN no Render."
            )

        self.access_token = str(
            tokens.get(
                "access_token",
                "",
            )
        ).strip()

        self.refresh_token = str(
            tokens.get(
                "refresh_token",
                "",
            )
        ).strip()

        if not self.access_token:
            raise RuntimeError(
                "Access token do Mercado Livre "
                "não encontrado."
            )

        if not self.refresh_token:
            raise RuntimeError(
                "Refresh token do Mercado Livre "
                "não encontrado."
            )

        print(
            "🔐 Tokens do Mercado Livre "
            "carregados do Neon."
        )

        # Se o banco já sabe que o token venceu,
        # renova antes mesmo da primeira chamada.
        if token_expirado(
            tokens
        ):
            print(
                "♻️ Access token expirado. "
                "Renovando antes da consulta..."
            )

            self._renovar_token()

    def _renovar_token(self):
        if self._auth_bloqueada:
            raise (
                MercadoLivreAuthenticationError(
                    "Autenticação do Mercado Livre "
                    "foi bloqueada nesta execução "
                    "após uma falha de renovação."
                )
            )

        try:
            # =================================================
            # TOKEN MANAGER FICA DENTRO DE auth/
            # =================================================

            from auth.token_manager import (
                renovar_access_token,
            )

            dados = renovar_access_token(
                refresh_token=
                    self.refresh_token
            )

            self.access_token = str(
                dados[
                    "access_token"
                ]
            ).strip()

            self.refresh_token = str(
                dados[
                    "refresh_token"
                ]
            ).strip()

            self._auth_bloqueada = False

        except Exception as erro:
            self._auth_bloqueada = True

            raise (
                MercadoLivreAuthenticationError(
                    "Falha ao renovar a "
                    "autenticação do Mercado Livre: "
                    f"{erro}"
                )
            ) from erro

    # =====================================================
    # HTTP
    # =====================================================

    def _headers(self):
        return {
            "Authorization":
                f"Bearer {self.access_token}",

            "Content-Type":
                "application/json",
        }

    def _request(
        self,
        metodo,
        endpoint,
        params=None,
        data=None,
        timeout=30,
    ):
        if self._auth_bloqueada:
            raise (
                MercadoLivreAuthenticationError(
                    "Autenticação do Mercado Livre "
                    "indisponível nesta execução."
                )
            )

        url = (
            f"{BASE_URL}{endpoint}"
        )

        try:
            resposta = requests.request(
                method=metodo,
                url=url,
                headers=self._headers(),
                params=params,
                json=data,
                timeout=timeout,
            )

        except requests.RequestException as erro:
            raise RuntimeError(
                "Erro ao consultar o "
                f"Mercado Livre em {url}: {erro}"
            ) from erro

        # =================================================
        # TOKEN EXPIROU / INVÁLIDO
        # =================================================

        if resposta.status_code == 401:
            print(
                "⚠️ Mercado Livre retornou 401. "
                "Tentando renovar o token..."
            )

            self._renovar_token()

            try:
                resposta = requests.request(
                    method=metodo,
                    url=url,
                    headers=self._headers(),
                    params=params,
                    json=data,
                    timeout=timeout,
                )

            except requests.RequestException as erro:
                raise RuntimeError(
                    "Erro ao repetir a consulta "
                    "após renovar o token "
                    f"em {url}: {erro}"
                ) from erro

            if resposta.status_code == 401:
                self._auth_bloqueada = True

                raise (
                    MercadoLivreAuthenticationError(
                        "O Mercado Livre continuou "
                        "retornando HTTP 401 mesmo "
                        "após a renovação do token."
                    )
                )

        return resposta

    def get(
        self,
        endpoint,
        params=None,
        timeout=30,
    ):
        return self._request(
            metodo="GET",
            endpoint=endpoint,
            params=params,
            timeout=timeout,
        )

    def post(
        self,
        endpoint,
        data=None,
        timeout=30,
    ):
        return self._request(
            metodo="POST",
            endpoint=endpoint,
            data=data,
            timeout=timeout,
        )