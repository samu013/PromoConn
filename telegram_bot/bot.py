import os

import requests
from dotenv import load_dotenv


load_dotenv()


TELEGRAM_TOKEN = os.getenv(
    "TELEGRAM_TOKEN"
)

# Mantemos o chat antigo apenas como fallback.
TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID"
)


if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "TELEGRAM_TOKEN não encontrado."
    )


# =========================================================
# FORMATAÇÃO
# =========================================================

def formatar_preco(valor):
    if valor is None:
        return None

    return (
        f"{float(valor):,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def montar_mensagem(
    produto
):
    nome = produto.get(
        "nome",
        "Oferta"
    )

    preco = produto.get(
        "preco"
    )

    preco_original = produto.get(
        "preco_original"
    )

    desconto = produto.get(
        "desconto"
    )

    link_afiliado = produto.get(
        "link_afiliado"
    )

    categoria = produto.get(
        "categoria"
    )

    linhas = []

    # =====================================================
    # CABEÇALHO
    # =====================================================

    linhas.append(
        "🔥 <b>OFERTA PROMOCONN</b>"
    )

    linhas.append("")

    linhas.append(
        f"<b>{nome}</b>"
    )

    # =====================================================
    # CATEGORIA
    # =====================================================

    if categoria:
        linhas.append("")

        linhas.append(
            f"📦 {categoria}"
        )

    # =====================================================
    # PREÇOS
    # =====================================================

    linhas.append("")

    if (
        preco_original is not None
        and preco is not None
        and preco_original > preco
    ):
        linhas.append(
            "❌ De: "
            f"<s>R$ "
            f"{formatar_preco(preco_original)}"
            f"</s>"
        )

    if preco is not None:
        linhas.append(
            "💰 <b>Por: R$ "
            f"{formatar_preco(preco)}"
            "</b>"
        )

    if desconto:
        linhas.append(
            f"📉 <b>{desconto:.0f}% OFF</b>"
        )

    # =====================================================
    # LINK
    # =====================================================

    if link_afiliado:
        linhas.append("")
        linhas.append(
            "🛒 <b>Comprar agora:</b>"
        )

        linhas.append(
            link_afiliado
        )

    linhas.append("")
    linhas.append(
        "⚡ PromoConn | Central de Promoções"
    )

    return "\n".join(
        linhas
    )


# =========================================================
# ENVIAR PRODUTO
# =========================================================

def enviar_produto(
    produto,
    chat_id=None
):
    """
    Envia o produto para um grupo específico.

    Se chat_id não for informado, usa
    TELEGRAM_CHAT_ID como fallback.
    """

    destino = (
        str(chat_id)
        if chat_id
        else TELEGRAM_CHAT_ID
    )

    if not destino:
        raise RuntimeError(
            "Nenhum chat_id definido "
            "para envio."
        )

    mensagem = montar_mensagem(
        produto
    )

    url = (
        "https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": destino,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    resposta = requests.post(
        url,
        json=payload,
        timeout=30,
    )

    try:
        dados = resposta.json()

    except ValueError:
        raise RuntimeError(
            "Telegram retornou uma "
            "resposta inválida."
        )

    if (
        resposta.status_code != 200
        or not dados.get("ok")
    ):
        raise RuntimeError(
            "Erro Telegram: "
            f"{dados}"
        )

    return dados