import re
import unicodedata

from database.database import conectar


# =========================================================
# CONFIGURAÇÕES
# =========================================================

PALAVRAS_GENERICAS = {
    "para",
    "com",
    "sem",
    "pro",
    "max",
    "mini",
    "kit",
    "cor",
    "tipo",
    "original",
}


TERMOS_ACESSORIOS = {
    "carregador",
    "cabo",
    "capa",
    "pelicula",
    "suporte",
    "base",
    "adaptador",
    "fone",
    "headset",
    "power bank",
    "controle remoto",
}


TERMOS_PRODUTO_PRINCIPAL = {
    "iphone",
    "samsung",
    "xiaomi",
    "poco",
    "redmi",
    "notebook",
    "tablet",
    "ps5",
    "playstation",
    "xbox",
    "geladeira",
    "alexa",
}


REGRAS_CATEGORIA = {
    "celular": {
        "Celulares",
    },

    "iphone": {
        "Celulares",
    },

    "samsung": {
        "Celulares",
        "Eletrônicos",
    },

    "xiaomi": {
        "Celulares",
        "Eletrônicos",
    },

    "poco": {
        "Celulares",
    },

    "redmi": {
        "Celulares",
    },

    "notebook": {
        "Informática",
    },

    "tablet": {
        "Informática",
        "Eletrônicos",
    },

    "ps5": {
        "Games",
    },

    "playstation": {
        "Games",
    },

    "xbox": {
        "Games",
    },

    "creatina": {
        "Esportes",
    },

    "geladeira": {
        "Eletrodomésticos",
    },

    "alexa": {
        "Eletrônicos",
    },
}


# =========================================================
# NORMALIZAÇÃO
# =========================================================

def normalizar(texto):
    if not texto:
        return ""

    texto = texto.lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    texto = re.sub(
        r"[^a-z0-9\s]",
        " ",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


def palavras_do_texto(texto):
    return set(
        normalizar(texto).split()
    )


# =========================================================
# PONTUAÇÃO
# =========================================================

def pontos_ranking(ranking):
    if ranking is None:
        return 0

    if ranking == 1:
        return 50

    if ranking <= 5:
        return 40

    if ranking <= 10:
        return 30

    if ranking <= 20:
        return 20

    return 0


def pontos_tendencia(posicao):
    if posicao is None:
        return 0

    if posicao <= 5:
        return 30

    if posicao <= 10:
        return 25

    if posicao <= 20:
        return 20

    if posicao <= 30:
        return 15

    return 10


# =========================================================
# ACESSÓRIOS
# =========================================================

def eh_acessorio(nome_produto):
    nome = normalizar(
        nome_produto
    )

    return any(
        termo in nome
        for termo in TERMOS_ACESSORIOS
    )


def tendencia_exige_produto_principal(
    palavra_tendencia
):
    palavras = set(
        normalizar(
            palavra_tendencia
        ).split()
    )

    return bool(
        palavras
        & TERMOS_PRODUTO_PRINCIPAL
    )


# =========================================================
# CATEGORIAS
# =========================================================

def categoria_compativel(
    palavra_tendencia,
    categoria_produto
):
    if not categoria_produto:
        return None

    palavras = normalizar(
        palavra_tendencia
    ).split()

    regras_encontradas = []

    for palavra in palavras:
        if palavra in REGRAS_CATEGORIA:
            regras_encontradas.append(
                REGRAS_CATEGORIA[palavra]
            )

    if not regras_encontradas:
        return None

    categorias_permitidas = set()

    for regra in regras_encontradas:
        categorias_permitidas.update(
            regra
        )

    return (
        categoria_produto
        in categorias_permitidas
    )


# =========================================================
# MATCH PRODUTO X TENDÊNCIA
# =========================================================

def combinar(
    nome_produto,
    palavra_tendencia,
    categoria_produto=None
):
    produto = palavras_do_texto(
        nome_produto
    )

    tendencia = [
        palavra
        for palavra
        in normalizar(
            palavra_tendencia
        ).split()
        if (
            len(palavra) >= 3
            and palavra
            not in PALAVRAS_GENERICAS
        )
    ]

    if not produto or not tendencia:
        return False

    compatibilidade = categoria_compativel(
        palavra_tendencia,
        categoria_produto
    )

    if compatibilidade is False:
        return False

    # Evita:
    #
    # tendência: iphone 17 pro max
    # produto: carregador para iphone
    #
    # ou:
    #
    # tendência: notebook
    # produto: suporte para notebook

    if (
        eh_acessorio(nome_produto)
        and tendencia_exige_produto_principal(
            palavra_tendencia
        )
    ):
        return False

    encontrados = [
        palavra
        for palavra in tendencia
        if palavra in produto
    ]

    if len(tendencia) == 1:
        return len(encontrados) == 1

    percentual = (
        len(encontrados)
        / len(tendencia)
    )

    return percentual >= 0.70


# =========================================================
# LINK AUTOMÁTICO DO PRODUTO
# =========================================================

def gerar_link_produto(
    ml_id,
    tipo,
    link_salvo=None
):
    if link_salvo:
        return link_salvo

    if (
        tipo == "PRODUCT"
        and ml_id
    ):
        return (
            "https://www.mercadolivre.com.br/"
            f"p/{ml_id}"
        )

    return None


# =========================================================
# CALCULAR OPORTUNIDADES
# =========================================================

def calcular_oportunidades(
    limite=None
):
    conexao = conectar()
    cursor = conexao.cursor()

    try:
        # =================================================
        # OPORTUNIDADES
        # =================================================

        cursor.execute("""
            SELECT
                id,
                ml_id,
                tipo,
                nome,
                imagem,
                categoria,
                ranking,
                link_produto,
                preco,
                preco_original,
                desconto,
                link_afiliado,
                status
            FROM oportunidades
            WHERE tipo = 'PRODUCT'
        """)

        oportunidades = (
            cursor.fetchall()
        )

        # =================================================
        # TENDÊNCIAS
        # =================================================

        cursor.execute("""
            SELECT
                palavra,
                posicao
            FROM tendencias
            WHERE ativo = 1
            ORDER BY posicao ASC
        """)

        tendencias = (
            cursor.fetchall()
        )

    finally:
        cursor.close()
        conexao.close()

    resultados = []

    # =====================================================
    # CALCULA SCORE
    # =====================================================

    for oportunidade in oportunidades:

        pontuacao = pontos_ranking(
            oportunidade["ranking"]
        )

        tendencias_encontradas = []

        for tendencia in tendencias:

            if combinar(
                oportunidade["nome"],
                tendencia["palavra"],
                oportunidade["categoria"]
            ):

                bonus = pontos_tendencia(
                    tendencia["posicao"]
                )

                pontuacao += bonus

                tendencias_encontradas.append(
                    {
                        "palavra":
                            tendencia["palavra"],

                        "posicao":
                            tendencia["posicao"],

                        "pontos":
                            bonus,

                        # Mantidos para compatibilidade
                        # com scripts antigos.
                        "termo":
                            tendencia["palavra"],

                        "ranking":
                            tendencia["posicao"],
                    }
                )

        link_produto = gerar_link_produto(
            ml_id=oportunidade["ml_id"],
            tipo=oportunidade["tipo"],
            link_salvo=
                oportunidade["link_produto"],
        )

        resultados.append(
            {
                "id":
                    oportunidade["id"],

                "ml_id":
                    oportunidade["ml_id"],

                "tipo":
                    oportunidade["tipo"],

                "nome":
                    oportunidade["nome"],

                "imagem":
                    oportunidade["imagem"],

                "categoria":
                    oportunidade["categoria"],

                "ranking":
                    oportunidade["ranking"],

                "pontuacao":
                    pontuacao,

                "link_produto":
                    link_produto,

                "preco":
                    oportunidade["preco"],

                "preco_original":
                    oportunidade[
                        "preco_original"
                    ],

                "desconto":
                    oportunidade["desconto"],

                "link_afiliado":
                    oportunidade[
                        "link_afiliado"
                    ],

                "status":
                    oportunidade["status"],

                "tendencias":
                    tendencias_encontradas,
            }
        )

    # =====================================================
    # ORDENAÇÃO
    # =====================================================

    resultados.sort(
        key=lambda produto:
            produto["pontuacao"],
        reverse=True
    )

    if limite is not None:
        resultados = resultados[
            :limite
        ]

    return resultados