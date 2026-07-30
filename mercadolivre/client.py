import json
import os
from pathlib import Path

import requests


BASE_URL = "https://api.mercadolibre.com"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = PROJECT_ROOT / "data" / "tokens.json"

ACCESS_TOKEN_ENV = "MERCADO_LIVRE_ACCESS_TOKEN"


class MercadoLivreClient:

    def __init__(self):
        self.access_token = self._carregar_access_token()

    def _carregar_access_token(self):
        """
        Carrega o Access Token nesta ordem:

        1. Variável de ambiente do Render:
           MERCADO_LIVRE_ACCESS_TOKEN

        2. Arquivo local:
           data/tokens.json
        """

        access_token_ambiente = os.getenv(
            ACCESS_TOKEN_ENV,
            "",
        ).strip()

        if access_token_ambiente:
            print(
                "🔐 Token do Mercado Livre carregado "
                "pela variável de ambiente."
            )
            return access_token_ambiente

        if TOKEN_FILE.exists():
            try:
                with TOKEN_FILE.open(
                    "r",
                    encoding="utf-8",
                ) as arquivo:
                    dados = json.load(arquivo)

            except json.JSONDecodeError as erro:
                raise RuntimeError(
                    f"O arquivo de tokens não contém "
                    f"um JSON válido: {TOKEN_FILE}"
                ) from erro

            access_token_arquivo = str(
                dados.get(
                    "access_token",
                    "",
                )
            ).strip()

            if not access_token_arquivo:
                raise RuntimeError(
                    f"O campo 'access_token' não foi "
                    f"encontrado em {TOKEN_FILE}."
                )

            print(
                "🔐 Token do Mercado Livre carregado "
                "pelo arquivo data/tokens.json."
            )
            return access_token_arquivo

        raise RuntimeError(
            "Token do Mercado Livre não encontrado. "
            f"Configure a variável de ambiente "
            f"{ACCESS_TOKEN_ENV} no Render ou crie o arquivo "
            f"{TOKEN_FILE}."
        )

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def get(
        self,
        endpoint,
        params=None,
        timeout=30,
    ):
        url = f"{BASE_URL}{endpoint}"

        try:
            return requests.get(
                url,
                headers=self._headers(),
                params=params,
                timeout=timeout,
            )

        except requests.RequestException as erro:
            raise RuntimeError(
                "Erro ao consultar o Mercado Livre "
                f"em {url}: {erro}"
            ) from erro

    def post(
        self,
        endpoint,
        data=None,
        timeout=30,
    ):
        url = f"{BASE_URL}{endpoint}"

        try:
            return requests.post(
                url,
                headers=self._headers(),
                json=data,
                timeout=timeout,
            )

        except requests.RequestException as erro:
            raise RuntimeError(
                "Erro ao enviar dados ao Mercado Livre "
                f"em {url}: {erro}"
            ) from erro