import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ML_REFRESH_TOKEN")

TOKEN_FILE = "data/tokens.json"


def salvar_tokens(dados):
    conteudo = {
        "access_token": dados["access_token"],
        "refresh_token": dados["refresh_token"],
        "expires_in": dados["expires_in"],
        "created_at": datetime.now().isoformat()
    }

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(conteudo, f, indent=4, ensure_ascii=False)

    print("✅ Tokens salvos com sucesso.")


def renovar_access_token():

    url = "https://api.mercadolibre.com/oauth/token"

    payload = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:

        dados = response.json()

        salvar_tokens(dados)

        return dados

    print(response.text)
    return None


if __name__ == "__main__":
    renovar_access_token()