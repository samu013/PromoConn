import os

import requests
from dotenv import load_dotenv


load_dotenv()


TELEGRAM_TOKEN = os.getenv(
    "TELEGRAM_TOKEN"
)

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID"
)


def formatar_reais(valor):
    if valor is None:
        return None

    texto = (
        f"{valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"R$ {texto}"


def montar_mensagem(produto):
    linhas = [
        "🔥 OFERTA NO MERCADO LIVRE",
        "",
        f"🛍️ {produto['nome']}",
        "",
    ]

    preco = produto.get("preco")

    preco_original = produto.get(
        "preco_original"
    )

    desconto = produto.get(
        "desconto"
    )

    if (
        preco_original
        and preco_original > preco
    ):
        linhas.append(
            "❌ De: "
            + formatar_reais(
                preco_original
            )
        )

    if preco is not None:
        linhas.append(
            "🔥 Por: "
            + formatar_reais(preco)
        )

    if desconto:
        linhas.append(
            f"💰 {desconto:.0f}% OFF"
        )

    linhas.extend(
        [
            "",
            "🛒 Clique no botão abaixo "
            "para conferir a oferta.",
            "",
            "⚠️ Preço e disponibilidade "
            "podem mudar.",
        ]
    )

    return "\n".join(linhas)


def enviar_produto(produto):
    if not TELEGRAM_TOKEN:
        raise ValueError(
            "TELEGRAM_TOKEN não encontrado "
            "no .env."
        )

    if not TELEGRAM_CHAT_ID:
        raise ValueError(
            "TELEGRAM_CHAT_ID não encontrado "
            "no .env."
        )

    link = produto.get(
        "link_afiliado"
    )

    if not link:
        raise ValueError(
            "Produto sem link de afiliado."
        )

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendPhoto"
    )

    mensagem = montar_mensagem(
        produto
    )

    teclado = {
        "inline_keyboard": [
            [
                {
                    "text":
                        "🛒 VER OFERTA",
                    "url":
                        link,
                }
            ]
        ]
    }

    dados = {
        "chat_id":
            TELEGRAM_CHAT_ID,

        "caption":
            mensagem,

        "reply_markup":
            __import__("json").dumps(
                teclado
            ),
    }

    imagem = produto.get(
        "imagem"
    )

    if imagem:
        dados["photo"] = imagem

        resposta = requests.post(
            url,
            data=dados,
            timeout=30
        )

    else:
        # Se não houver imagem, envia
        # mensagem normal.

        url = (
            f"https://api.telegram.org/"
            f"bot{TELEGRAM_TOKEN}/"
            f"sendMessage"
        )

        dados.pop(
            "caption",
            None
        )

        dados["text"] = mensagem

        resposta = requests.post(
            url,
            data=dados,
            timeout=30
        )

    if not resposta.ok:
        raise RuntimeError(
            "Erro ao enviar Telegram: "
            + resposta.text
        )

    return resposta.json()