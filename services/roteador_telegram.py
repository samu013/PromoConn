import re
import unicodedata

from database.canais_telegram import (
    buscar_canal_por_categoria,
)


CATEGORIA_GERAL = "Geral"


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
        if not unicodedata.combining(
            caractere
        )
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


def descobrir_categoria_destino(
    produto
):
    nome = normalizar(
        produto.get("nome")
    )

    categoria = normalizar(
        produto.get("categoria")
    )

    texto = (
        f"{categoria} {nome}"
    )

    # =========================================
    # MODA FEMININA
    # =========================================

    termos_femininos = (
        "feminino",
        "feminina",
        "mulher",
        "vestido",
        "saia",
        "sutia",
        "lingerie",
        "bolsa feminina",
    )

    if any(
        termo in texto
        for termo in termos_femininos
    ):
        return "Moda Feminina"

    # =========================================
    # MODA MASCULINA
    # =========================================

    termos_masculinos = (
        "masculino",
        "masculina",
        "homem",
        "camisa polo",
        "cueca",
        "bermuda masculina",
    )

    if any(
        termo in texto
        for termo in termos_masculinos
    ):
        return "Moda Masculina"

    # =========================================
    # ESPORTES
    # =========================================

    termos_esportes = (
        "esporte",
        "esportes",
        "chuteira",
        "futebol",
        "academia",
        "halter",
        "creatina",
        "whey",
        "bicicleta",
    )

    if any(
        termo in texto
        for termo in termos_esportes
    ):
        return "Esportes"

    # =========================================
    # GAMES
    # =========================================

    termos_games = (
        "games",
        "game",
        "ps5",
        "playstation",
        "xbox",
        "nintendo",
        "joystick",
        "videogame",
    )

    if any(
        termo in texto
        for termo in termos_games
    ):
        return "Games"

    # =========================================
    # CELULARES
    # =========================================

    termos_celulares = (
        "celular",
        "smartphone",
        "iphone",
        "samsung galaxy",
        "xiaomi",
        "poco",
        "redmi",
    )

    if any(
        termo in texto
        for termo in termos_celulares
    ):
        return "Celulares"

    # =========================================
    # INFORMÁTICA
    # =========================================

    termos_informatica = (
        "informatica",
        "notebook",
        "computador",
        "pc gamer",
        "monitor",
        "teclado",
        "mouse",
        "ssd",
        "processador",
        "ryzen",
    )

    if any(
        termo in texto
        for termo in termos_informatica
    ):
        return "Informática"

    # =========================================
    # CASA
    # =========================================

    termos_casa = (
        "casa",
        "geladeira",
        "guarda roupa",
        "cozinha",
        "liquidificador",
        "lavadora",
        "ferramentas",
    )

    if any(
        termo in texto
        for termo in termos_casa
    ):
        return "Casa"

    return CATEGORIA_GERAL


def buscar_destino_produto(
    produto
):
    categoria_destino = (
        descobrir_categoria_destino(
            produto
        )
    )

    canal = buscar_canal_por_categoria(
        categoria_destino
    )

    if canal:
        return canal

    # fallback para grupo geral
    return buscar_canal_por_categoria(
        CATEGORIA_GERAL
    )