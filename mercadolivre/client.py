import json
import os
import requests

BASE_URL = "https://api.mercadolibre.com"
TOKEN_FILE = os.path.join("data", "tokens.json")


class MercadoLivreClient:

    def __init__(self):
        self.access_token = self._carregar_access_token()

    def _carregar_access_token(self):
        """Lê o Access Token salvo no arquivo."""

        with open(TOKEN_FILE, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        return dados["access_token"]

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def get(self, endpoint, params=None):

        url = f"{BASE_URL}{endpoint}"

        resposta = requests.get(
            url,
            headers=self._headers(),
            params=params
        )

        return resposta

    def post(self, endpoint, data=None):

        url = f"{BASE_URL}{endpoint}"

        resposta = requests.post(
            url,
            headers=self._headers(),
            json=data
        )

        return resposta