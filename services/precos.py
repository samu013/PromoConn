import json
import re

import requests


BASE_URL = "https://www.mercadolivre.com.br"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


# =========================================================
# AUXILIARES
# =========================================================

def calcular_desconto(
    preco,
    preco_original
):
    if (
        preco is None
        or preco_original is None
    ):
        return None

    try:
        preco = float(preco)
        preco_original = float(
            preco_original
        )

    except (TypeError, ValueError):
        return None

    if (
        preco <= 0
        or preco_original <= preco
    ):
        return None

    return round(
        (
            (
                preco_original - preco
            )
            / preco_original
        )
        * 100,
        2,
    )


def montar_url_produto(
    product_id,
    item_id=None
):
    url = (
        f"{BASE_URL}/p/{product_id}"
    )

    if item_id:
        url += (
            "?pdp_filters="
            f"item_id%3A{item_id}"
        )

    return url


# =========================================================
# EXTRAIR JSON DO HTML
# =========================================================

def _extrair_objeto_json(
    texto,
    inicio
):
    """
    Encontra um objeto JSON {...}
    começando a partir de 'inicio'.

    Faz contagem de chaves e respeita strings.
    """

    posicao = texto.find(
        "{",
        inicio
    )

    if posicao == -1:
        return None

    nivel = 0
    dentro_string = False
    escapado = False

    for indice in range(
        posicao,
        len(texto)
    ):
        caractere = texto[indice]

        if dentro_string:

            if escapado:
                escapado = False

            elif caractere == "\\":
                escapado = True

            elif caractere == '"':
                dentro_string = False

            continue

        if caractere == '"':
            dentro_string = True

        elif caractere == "{":
            nivel += 1

        elif caractere == "}":
            nivel -= 1

            if nivel == 0:
                return texto[
                    posicao:indice + 1
                ]

    return None


def extrair_contexto_nordic(html):
    marcador = "_n.ctx.r ="

    inicio = html.find(
        marcador
    )

    if inicio == -1:
        return None

    json_texto = _extrair_objeto_json(
        html,
        inicio + len(marcador)
    )

    if not json_texto:
        return None

    try:
        return json.loads(
            json_texto
        )

    except json.JSONDecodeError:
        return None


# =========================================================
# LOCALIZAR DADOS DA PDP
# =========================================================

def extrair_dados_produto(html):
    contexto = extrair_contexto_nordic(
        html
    )

    if contexto:
        try:
            componentes = (
                contexto["appProps"]
                ["pageProps"]
                ["initialState"]
                ["components"]
            )

            track = componentes.get(
                "track",
                {}
            )

            dados = (
                track
                .get(
                    "melidata_event",
                    {}
                )
                .get(
                    "event_data",
                    {}
                )
            )

            if dados:
                preco = dados.get(
                    "price"
                )

                preco_original = (
                    dados.get(
                        "original_price"
                    )
                )

                desconto = calcular_desconto(
                    preco,
                    preco_original,
                )

                # Em algumas páginas já existe
                # o desconto pronto.
                pricing = (
                    dados
                    .get(
                        "credit_view_components",
                        {}
                    )
                    .get(
                        "pricing",
                        {}
                    )
                )

                desconto_texto = (
                    pricing.get(
                        "discount"
                    )
                )

                if desconto_texto:
                    try:
                        desconto = float(
                            desconto_texto
                            .replace(
                                "%",
                                ""
                            )
                        )
                    except ValueError:
                        pass

                reviews = dados.get(
                    "reviews",
                    {}
                )

                return {
                    "product_id":
                        dados.get(
                            "catalog_product_id"
                        ),

                    "item_id":
                        dados.get(
                            "item_id"
                        ),

                    "categoria_id":
                        dados.get(
                            "category_id"
                        ),

                    "preco":
                        preco,

                    "preco_original":
                        preco_original,

                    "desconto":
                        desconto,

                    "moeda":
                        dados.get(
                            "currency_id",
                            "BRL"
                        ),

                    "estoque":
                        dados.get(
                            "quantity"
                        ),

                    "tem_estoque":
                        dados.get(
                            "has_stock"
                        ),

                    "vendidos":
                        dados.get(
                            "sold_quantity"
                        ),

                    "avaliacao":
                        reviews.get(
                            "rate"
                        ),

                    "avaliacoes":
                        reviews.get(
                            "count"
                        ),

                    "ranking":
                        dados.get(
                            "best_seller_position"
                        ),

                    "seller_id":
                        dados.get(
                            "seller_id"
                        ),

                    "seller_name":
                        dados.get(
                            "seller_name"
                        ),

                    "fonte":
                        "pagina_publica",
                }

        except (
            KeyError,
            TypeError,
        ):
            pass

    # =====================================================
    # FALLBACK
    #
    # Caso a estrutura Nordic mude, tenta pelo menos
    # recuperar preço pelo OpenGraph.
    # =====================================================

    og_title = re.search(
        r'<meta\s+property="og:title"\s+'
        r'content="[^"]*-\s*R\$\s*'
        r'([0-9.,]+)"',
        html,
        re.IGNORECASE,
    )

    if og_title:
        preco_texto = (
            og_title.group(1)
            .replace(".", "")
            .replace(",", ".")
        )

        try:
            preco = float(
                preco_texto
            )

            return {
                "product_id": None,
                "item_id": None,
                "categoria_id": None,
                "preco": preco,
                "preco_original": None,
                "desconto": None,
                "moeda": "BRL",
                "estoque": None,
                "tem_estoque": None,
                "vendidos": None,
                "avaliacao": None,
                "avaliacoes": None,
                "ranking": None,
                "seller_id": None,
                "seller_name": None,
                "fonte": "opengraph",
            }

        except ValueError:
            pass

    return None


# =========================================================
# CONSULTAR PÁGINA
# =========================================================

def buscar_preco_pagina(
    product_id,
    item_id=None
):
    url = montar_url_produto(
        product_id,
        item_id,
    )

    try:
        resposta = requests.get(
            url,
            headers=HEADERS,
            timeout=20,
        )

    except requests.RequestException as erro:
        print(
            "[PREÇO PÁGINA] "
            f"Erro: {erro}"
        )

        return None

    print(
        "[PREÇO PÁGINA] "
        f"{product_id} "
        f"→ HTTP {resposta.status_code}"
    )

    if resposta.status_code != 200:
        return None

    resultado = extrair_dados_produto(
        resposta.text
    )

    if not resultado:
        print(
            "[PREÇO PÁGINA] "
            "Dados não encontrados."
        )

        return None

    resultado["url"] = (
        resposta.url
    )

    return resultado


# =========================================================
# FUNÇÃO PRINCIPAL
# =========================================================

def buscar_preco(
    product_id,
    item_id=None
):
    """
    Busca os dados atuais da página pública do produto.

    product_id:
        MLB25929487

    item_id opcional:
        MLB4812130742
    """

    resultado = buscar_preco_pagina(
        product_id,
        item_id,
    )

    if resultado:
        return resultado

    print(
        "[PREÇO] Não foi possível "
        "obter os dados automaticamente."
    )

    return None