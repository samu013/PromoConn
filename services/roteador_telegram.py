import re
import unicodedata

from database.canais_telegram import (
    buscar_canal_por_categoria,
)


CATEGORIA_GERAL = "Geral"


# =========================================================
# CATEGORIAS OFICIAIS DO PROMOCONN
# =========================================================

CATEGORIAS_PROMOCONN = {
    "celulares": "Celulares",
    "games": "Games",
    "tecnologia": "Tecnologia",
    "informatica": "Tecnologia",
    "casa": "Casa",
    "esportes": "Esportes",
    "moda feminina": "Moda Feminina",
    "moda masculina": "Moda Masculina",
    "beleza": "Beleza e Cuidados",
    "beleza e cuidados": "Beleza e Cuidados",
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


# =========================================================
# DESCOBRE CATEGORIA
# =========================================================

def descobrir_categoria_destino(
    produto
):
    # =====================================================
    # 1. PRIORIZA A CATEGORIA JÁ SALVA
    # =====================================================

    categoria_original = normalizar(
        produto.get(
            "categoria"
        )
    )

    if (
        categoria_original
        in CATEGORIAS_PROMOCONN
    ):
        return CATEGORIAS_PROMOCONN[
            categoria_original
        ]

    # =====================================================
    # 2. FALLBACK PELO NOME
    # =====================================================

    nome = normalizar(
        produto.get(
            "nome"
        )
    )

    texto = (
        f"{categoria_original} {nome}"
    )

    # =====================================================
    # BELEZA E CUIDADOS
    # =====================================================

    termos_beleza = (
        "beleza",
        "cosmetico",
        "cosmeticos",
        "maquiagem",
        "batom",
        "rimel",
        "mascara de cilios",
        "base facial",
        "corretivo",
        "perfume",
        "perfumaria",
        "shampoo",
        "condicionador",
        "hidratante",
        "skincare",
        "skin care",
        "protetor solar",
        "creme facial",
        "creme corporal",
        "serum",
        "serum facial",
        "barbeador",
        "barba",
        "kit barba",
        "depilador",
        "secador de cabelo",
        "chapinha",
        "prancha de cabelo",
    )

    if any(
        termo in texto
        for termo in termos_beleza
    ):
        return "Beleza e Cuidados"

    # =====================================================
    # MODA FEMININA
    # =====================================================

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

    # =====================================================
    # MODA MASCULINA
    # =====================================================

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

    # =====================================================
    # ESPORTES
    # =====================================================

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

    # =====================================================
    # GAMES
    # =====================================================

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

    # =====================================================
    # CELULARES
    # =====================================================

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

    # =====================================================
    # TECNOLOGIA
    # =====================================================

    termos_tecnologia = (
        "tecnologia",
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
        for termo in termos_tecnologia
    ):
        return "Tecnologia"

    # =====================================================
    # CASA
    # =====================================================

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

    # =====================================================
    # SEM CATEGORIA ESPECÍFICA
    # =====================================================

    return CATEGORIA_GERAL


# =========================================================
# BUSCA DESTINO
# =========================================================

def buscar_destino_produto(
    produto
):
    categoria_destino = (
        descobrir_categoria_destino(
            produto
        )
    )

    print(
        "📌 Roteamento Telegram:"
    )

    print(
        "   Categoria salva:",
        produto.get(
            "categoria"
        )
    )

    print(
        "   Categoria destino:",
        categoria_destino
    )

    canal = (
        buscar_canal_por_categoria(
            categoria_destino
        )
    )

    if canal:
        print(
            "   ✅ Canal encontrado:",
            canal.get(
                "nome"
            )
        )

        return canal

    print(
        "   ⚠️ Canal específico não encontrado."
    )

    print(
        "   ↪ Usando grupo Geral."
    )

    return buscar_canal_por_categoria(
        CATEGORIA_GERAL
    )