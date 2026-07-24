import os

import requests
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "TELEGRAM_TOKEN não encontrado no .env"
    )


url = (
    f"https://api.telegram.org/"
    f"bot{TOKEN}/getUpdates"
)

resposta = requests.get(
    url,
    timeout=30
)

resposta.raise_for_status()

dados = resposta.json()


print()
print("=" * 70)
print("GRUPOS ENCONTRADOS")
print("=" * 70)


grupos = {}


for update in dados.get("result", []):

    mensagem = (
        update.get("message")
        or update.get("channel_post")
        or update.get("my_chat_member")
    )

    if not mensagem:
        continue

    chat = mensagem.get(
        "chat",
        {}
    )

    chat_id = chat.get("id")

    titulo = (
        chat.get("title")
        or chat.get("username")
        or chat.get("first_name")
    )

    tipo = chat.get("type")

    if tipo not in (
        "group",
        "supergroup",
        "channel",
    ):
        continue

    grupos[chat_id] = {
        "titulo": titulo,
        "tipo": tipo,
    }


if not grupos:
    print()
    print("Nenhum grupo encontrado.")
    print()
    print(
        "Envie uma mensagem em cada grupo "
        "e execute novamente."
    )

else:

    for chat_id, grupo in grupos.items():

        print()
        print(
            f"Grupo: {grupo['titulo']}"
        )

        print(
            f"Tipo: {grupo['tipo']}"
        )

        print(
            f"Chat ID: {chat_id}"
        )

        print("-" * 70)