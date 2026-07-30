import re
import time
import unicodedata

from database.database import criar_tabelas
from database.oportunidades import salvar_oportunidade
from database.tendencias import (
    desativar_todas,
    salvar_tendencia,
)

from mercadolivre.highlights import Highlights
from mercadolivre.trends import Trends


# =========================================================
# CONFIGURAÇÃO
# =========================================================

INTERVALO_SEGUNDOS = 60 * 60

EXPANDIR_SUBCATEGORIAS = True
MAX_SUBCATEGORIAS_POR_GRUPO = 10


# Cada grupo possui:
#
# id:
#   categoria usada no endpoint de Highlights.
#
# expandir:
#   define se as subcategorias diretas serão consultadas.
#
# filtro:
#   opcional. É usado em Moda Feminina e Moda Masculina
#   para evitar que os mesmos produtos entrem nos dois
#   grupos.
GRUPOS = {
    "Celulares": {
        "id": "MLB1055",
        "expandir": True,
        "filtro": None,
    },

    "Games": {
        "id": "MLB1144",
        "expandir": True,
        "filtro": None,
    },

    "Tecnologia": {
        "id": "MLB1648",
        "expandir": True,
        "filtro": None,
    },

    "Casa": {
        "id": "MLB1574",
        "expandir": True,
        "filtro": None,
    },

    "Esportes": {
        "id": "MLB264201",
        "expandir": True,
        "filtro": None,
    },

    # Categoria principal oficial:
    # Calçados, Roupas e Bolsas.
    #
    # Os dois grupos consultam a mesma categoria principal,
    # mas cada um aplica um filtro pelo nome do produto.
    "Moda Feminina": {
        "id": "MLB1430",
        "expandir": True,
        "filtro": "feminino",
    },

    "Moda Masculina": {
        "id": "MLB1430",
        "expandir": True,
        "filtro": "masculino",
    },
}


PALAVRAS_FEMININAS = {
    "feminina",
    "feminino",
    "mulher",
    "mulheres",
    "dama",
    "vestido",
    "saia",
    "saias",
    "blusa",
    "blusas",
    "cropped",
    "legging",
    "leggings",
    "lingerie",
    "calcinha",
    "calcinhas",
    "sutia",
    "sutiã",
    "sutiãs",
    "body feminino",
    "bolsa feminina",
    "sandalia feminina",
    "sandália feminina",
    "sapatilha",
    "salto feminino",
}

PALAVRAS_MASCULINAS = {
    "masculina",
    "masculino",
    "homem",
    "homens",
    "bermuda masculina",
    "camisa masculina",
    "camiseta masculina",
    "calca masculina",
    "calça masculina",
    "cueca",
    "cuecas",
    "terno",
    "ternos",
    "gravata",
    "gravatas",
    "sapato masculino",
    "tenis masculino",
    "tênis masculino",
}


# =========================================================
# TEXTO / CLASSIFICAÇÃO
# =========================================================

def normalizar_texto(texto):
    texto = str(
        texto
        or ""
    ).lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(
            caractere
        )
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    ).strip()

    return texto


PALAVRAS_FEMININAS_NORMALIZADAS = {
    normalizar_texto(palavra)
    for palavra in PALAVRAS_FEMININAS
}

PALAVRAS_MASCULINAS_NORMALIZADAS = {
    normalizar_texto(palavra)
    for palavra in PALAVRAS_MASCULINAS
}


def contem_alguma_palavra(
    texto,
    palavras,
):
    return any(
        palavra in texto
        for palavra in palavras
    )


def produto_pertence_ao_filtro(
    nome,
    filtro,
):
    if not filtro:
        return True

    texto = normalizar_texto(
        nome
    )

    feminino = contem_alguma_palavra(
        texto,
        PALAVRAS_FEMININAS_NORMALIZADAS,
    )

    masculino = contem_alguma_palavra(
        texto,
        PALAVRAS_MASCULINAS_NORMALIZADAS,
    )

    if filtro == "feminino":
        return (
            feminino
            and not masculino
        )

    if filtro == "masculino":
        return (
            masculino
            and not feminino
        )

    return True


# =========================================================
# TENDÊNCIAS
# =========================================================

def coletar_tendencias():
    print()
    print("=" * 70)
    print("COLETANDO TENDÊNCIAS")
    print("=" * 70)

    trends = Trends()
    tendencias = trends.buscar()

    if not tendencias:
        print(
            "Nenhuma tendência retornada."
        )
        return 0

    print(
        f"Tendências recebidas: "
        f"{len(tendencias)}"
    )

    desativar_todas()

    total_salvas = 0

    for posicao, tendencia in enumerate(
        tendencias,
        start=1,
    ):
        if isinstance(
            tendencia,
            str,
        ):
            palavra = tendencia
            url = None
            posicao_api = posicao

        elif isinstance(
            tendencia,
            dict,
        ):
            palavra = (
                tendencia.get("keyword")
                or tendencia.get("palavra")
                or tendencia.get("name")
                or tendencia.get("query")
            )

            url = tendencia.get("url")

            posicao_api = (
                tendencia.get("position")
                or tendencia.get("posicao")
                or posicao
            )

        else:
            continue

        if not palavra:
            continue

        salvar_tendencia(
            palavra=palavra,
            url=url,
            posicao=posicao_api,
        )

        total_salvas += 1

    print(
        f"Tendências salvas: "
        f"{total_salvas}"
    )

    return total_salvas


# =========================================================
# CATEGORIAS / SUBCATEGORIAS
# =========================================================

def buscar_subcategorias(
    client,
    categoria_id,
    expandir=True,
):
    if (
        not EXPANDIR_SUBCATEGORIAS
        or not expandir
    ):
        return []

    try:
        resposta = client.get(
            f"/categories/{categoria_id}"
        )

    except Exception as erro:
        print(
            "  Não foi possível consultar "
            f"subcategorias: {erro}"
        )
        return []

    if resposta.status_code != 200:
        print(
            "  Subcategorias indisponíveis "
            f"(HTTP {resposta.status_code})."
        )
        return []

    try:
        dados = resposta.json()

    except Exception:
        return []

    filhos = dados.get(
        "children_categories",
        [],
    )

    if not isinstance(
        filhos,
        list,
    ):
        return []

    subcategorias = []

    for filho in filhos:
        if not isinstance(
            filho,
            dict,
        ):
            continue

        subcategoria_id = filho.get(
            "id"
        )

        subcategoria_nome = filho.get(
            "name"
        )

        if not subcategoria_id:
            continue

        # A dimensão "Outros" costuma não existir no endpoint
        # de Highlights e gerar 404.
        if normalizar_texto(
            subcategoria_nome
        ) == "outros":
            continue

        subcategorias.append({
            "id":
                subcategoria_id,

            "name": (
                subcategoria_nome
                or subcategoria_id
            ),
        })

        if (
            len(subcategorias)
            >= MAX_SUBCATEGORIAS_POR_GRUPO
        ):
            break

    return subcategorias


def montar_categorias_coleta(
    highlights,
    categoria_nome,
    configuracao,
):
    categoria_id = configuracao[
        "id"
    ]

    categorias = [{
        "id":
            categoria_id,

        "nome_api":
            categoria_nome,

        "categoria_salva":
            categoria_nome,

        "principal":
            True,
    }]

    subcategorias = buscar_subcategorias(
        highlights.client,
        categoria_id,
        expandir=configuracao.get(
            "expandir",
            True,
        ),
    )

    for subcategoria in subcategorias:
        categorias.append({
            "id":
                subcategoria["id"],

            "nome_api":
                subcategoria["name"],

            "categoria_salva":
                categoria_nome,

            "principal":
                False,
        })

    return categorias


# =========================================================
# SALVAR RESULTADOS
# =========================================================

def processar_produtos_highlight(
    produtos,
    categoria_salva,
    filtro=None,
):
    recebidos = len(
        produtos
    )

    novos = 0
    conhecidos_ou_recentes = 0
    filtrados = 0
    invalidos = 0
    erros = 0

    for produto in produtos:
        if not isinstance(
            produto,
            dict,
        ):
            invalidos += 1
            continue

        ml_id = produto.get(
            "id"
        )

        tipo = (
            produto.get("tipo")
            or produto.get("type")
        )

        nome = (
            produto.get("nome")
            or produto.get("name")
            or produto.get("title")
        )

        if (
            not ml_id
            or not tipo
            or not nome
        ):
            invalidos += 1
            continue

        if not produto_pertence_ao_filtro(
            nome,
            filtro,
        ):
            filtrados += 1
            continue

        oportunidade = {
            "id":
                ml_id,

            "tipo":
                tipo,

            "nome":
                nome,

            "imagem": (
                produto.get("imagem")
                or produto.get("picture")
                or produto.get("thumbnail")
            ),

            "ranking": (
                produto.get("ranking")
                or produto.get("position")
            ),
        }

        try:
            novo = salvar_oportunidade(
                produto=oportunidade,
                fonte="highlights",
                categoria=categoria_salva,
            )

            if novo:
                novos += 1
            else:
                conhecidos_ou_recentes += 1

        except Exception as erro:
            erros += 1

            print(
                f"    Erro ao salvar "
                f"{ml_id}: {erro}"
            )

    return {
        "recebidos":
            recebidos,

        "novos":
            novos,

        "conhecidos_ou_recentes":
            conhecidos_ou_recentes,

        "filtrados":
            filtrados,

        "invalidos":
            invalidos,

        "erros":
            erros,
    }


# =========================================================
# HIGHLIGHTS
# =========================================================

def coletar_highlights():
    print()
    print("=" * 70)
    print("COLETANDO HIGHLIGHTS")
    print("=" * 70)

    highlights = Highlights()

    total_consultas = 0
    total_recebidos = 0
    total_novos = 0
    total_conhecidos = 0
    total_filtrados = 0
    total_invalidos = 0
    total_erros = 0

    for (
        categoria_nome,
        configuracao,
    ) in GRUPOS.items():

        print()
        print("#" * 70)
        print(
            f"GRUPO: {categoria_nome}"
        )
        print("#" * 70)

        categorias_coleta = (
            montar_categorias_coleta(
                highlights,
                categoria_nome,
                configuracao,
            )
        )

        print(
            "Categoria principal: "
            f"{configuracao['id']}"
        )

        print(
            "Subcategorias selecionadas: "
            f"{len(categorias_coleta) - 1}"
        )

        grupo_recebidos = 0
        grupo_novos = 0
        grupo_conhecidos = 0
        grupo_filtrados = 0

        for categoria in categorias_coleta:
            total_consultas += 1

            prefixo = (
                "Principal"
                if categoria["principal"]
                else "Subcategoria"
            )

            print()
            print(
                f"  [{prefixo}] "
                f"{categoria['nome_api']} "
                f"({categoria['id']})"
            )

            try:
                produtos = highlights.buscar(
                    categoria["id"]
                )

            except Exception as erro:
                total_erros += 1

                print(
                    "    Erro ao buscar: "
                    f"{erro}"
                )
                continue

            if not produtos:
                print(
                    "    Nenhum produto retornado."
                )
                continue

            resultado = (
                processar_produtos_highlight(
                    produtos,
                    categoria[
                        "categoria_salva"
                    ],
                    filtro=configuracao.get(
                        "filtro"
                    ),
                )
            )

            total_recebidos += resultado[
                "recebidos"
            ]

            total_novos += resultado[
                "novos"
            ]

            total_conhecidos += resultado[
                "conhecidos_ou_recentes"
            ]

            total_filtrados += resultado[
                "filtrados"
            ]

            total_invalidos += resultado[
                "invalidos"
            ]

            total_erros += resultado[
                "erros"
            ]

            grupo_recebidos += resultado[
                "recebidos"
            ]

            grupo_novos += resultado[
                "novos"
            ]

            grupo_conhecidos += resultado[
                "conhecidos_ou_recentes"
            ]

            grupo_filtrados += resultado[
                "filtrados"
            ]

            print(
                "    Recebidos: "
                f"{resultado['recebidos']}"
            )

            print(
                "    Novos: "
                f"{resultado['novos']}"
            )

            print(
                "    Já existentes/recentes: "
                f"{resultado['conhecidos_ou_recentes']}"
            )

            if resultado["filtrados"]:
                print(
                    "    Fora do perfil do grupo: "
                    f"{resultado['filtrados']}"
                )

            if resultado["invalidos"]:
                print(
                    "    Inválidos: "
                    f"{resultado['invalidos']}"
                )

            if resultado["erros"]:
                print(
                    "    Erros: "
                    f"{resultado['erros']}"
                )

        print()
        print(
            f"  RESUMO {categoria_nome.upper()}"
        )

        print(
            f"  Recebidos: "
            f"{grupo_recebidos}"
        )

        print(
            f"  Novos: "
            f"{grupo_novos}"
        )

        print(
            "  Já existentes/recentes: "
            f"{grupo_conhecidos}"
        )

        if configuracao.get(
            "filtro"
        ):
            print(
                "  Fora do perfil do grupo: "
                f"{grupo_filtrados}"
            )

    print()
    print("=" * 70)
    print("RESUMO FINAL DOS HIGHLIGHTS")
    print("=" * 70)

    print(
        f"Consultas realizadas: "
        f"{total_consultas}"
    )

    print(
        f"Produtos recebidos: "
        f"{total_recebidos}"
    )

    print(
        f"Novas oportunidades: "
        f"{total_novos}"
    )

    print(
        "Já existentes/recentes: "
        f"{total_conhecidos}"
    )

    print(
        "Fora do perfil dos grupos: "
        f"{total_filtrados}"
    )

    print(
        f"Inválidos: "
        f"{total_invalidos}"
    )

    print(
        f"Erros: "
        f"{total_erros}"
    )

    return total_novos


# =========================================================
# CICLO
# =========================================================

def executar_coleta():
    print()
    print("=" * 70)
    print("PROMOCONN - COLETA AUTOMÁTICA")
    print("=" * 70)

    try:
        coletar_tendencias()

    except Exception as erro:
        print(
            "Erro geral nas tendências:"
        )
        print(erro)

    try:
        coletar_highlights()

    except Exception as erro:
        print(
            "Erro geral nos highlights:"
        )
        print(erro)


# =========================================================
# WORKER
# =========================================================

def executar_worker():
    criar_tabelas()

    print()
    print("=" * 70)
    print("PROMOCONN COLETOR WORKER")
    print("=" * 70)

    print(
        "Intervalo de coleta: 1 hora"
    )

    print(
        "Expansão de subcategorias: "
        + (
            "ATIVA"
            if EXPANDIR_SUBCATEGORIAS
            else "DESATIVADA"
        )
    )

    while True:
        try:
            executar_coleta()

        except Exception as erro:
            print()
            print(
                "Erro inesperado no ciclo:"
            )
            print(erro)

        print()
        print(
            "Próxima coleta em 1 hora."
        )
        print()

        time.sleep(
            INTERVALO_SEGUNDOS
        )


if __name__ == "__main__":
    executar_worker()
