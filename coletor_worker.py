import time

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


# Categorias principais que já estavam funcionando.
#
# O coletor agora também pode consultar automaticamente
# subcategorias diretas de cada uma delas, usando o endpoint
# oficial /categories/{id}.
CATEGORIAS = {
    "Celulares": "MLB1055",
    "Games": "MLB1144",
    "Tecnologia": "MLB1648",
    "Casa": "MLB1574",
    "Esportes": "MLB264201",
}


# =========================================================
# DIVERSIDADE DA COLETA
# =========================================================

# True:
#   consulta a categoria principal + subcategorias diretas.
#
# False:
#   mantém exatamente o comportamento antigo.
EXPANDIR_SUBCATEGORIAS = True


# Limite de subcategorias por grupo principal.
#
# Isso evita centenas de chamadas numa única coleta.
# Você pode aumentar depois, se quiser.
MAX_SUBCATEGORIAS_POR_GRUPO = 10


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

    # Marca as antigas como inativas.
    # As encontradas novamente serão reativadas.
    desativar_todas()

    total_salvas = 0

    for posicao, tendencia in enumerate(
        tendencias,
        start=1,
    ):
        # Permite alguns formatos diferentes.
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
                tendencia.get(
                    "keyword"
                )
                or tendencia.get(
                    "palavra"
                )
                or tendencia.get(
                    "name"
                )
                or tendencia.get(
                    "query"
                )
            )

            url = tendencia.get(
                "url"
            )

            posicao_api = (
                tendencia.get(
                    "position"
                )
                or tendencia.get(
                    "posicao"
                )
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
):
    """
    Busca as subcategorias diretas de uma categoria.

    Retorna uma lista no formato:

    [
        {
            "id": "MLB...",
            "name": "..."
        }
    ]

    Se a consulta falhar, simplesmente retorna [] e
    a coleta da categoria principal continua normalmente.
    """

    if not EXPANDIR_SUBCATEGORIAS:
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

        subcategoria_id = (
            filho.get(
                "id"
            )
        )

        subcategoria_nome = (
            filho.get(
                "name"
            )
        )

        if not subcategoria_id:
            continue

        subcategorias.append({
            "id": subcategoria_id,
            "name": (
                subcategoria_nome
                or subcategoria_id
            ),
        })

        if (
            len(
                subcategorias
            )
            >= MAX_SUBCATEGORIAS_POR_GRUPO
        ):
            break

    return subcategorias


def montar_categorias_coleta(
    highlights,
    categoria_nome,
    categoria_id,
):
    """
    Monta a lista de endpoints de Highlights a consultar.

    Primeiro entra a categoria principal.
    Depois, se habilitado, entram as subcategorias diretas.
    """

    categorias = [{
        "id": categoria_id,
        "nome_api": categoria_nome,
        "categoria_salva": categoria_nome,
        "principal": True,
    }]

    subcategorias = buscar_subcategorias(
        highlights.client,
        categoria_id,
    )

    for subcategoria in subcategorias:
        categorias.append({
            "id":
                subcategoria["id"],

            "nome_api":
                subcategoria["name"],

            # Mantemos a categoria principal no banco
            # para não quebrar o roteamento atual dos
            # canais Telegram.
            "categoria_salva":
                categoria_nome,

            "principal":
                False,
        })

    return categorias


# =========================================================
# SALVAR RESULTADOS DE UMA CATEGORIA
# =========================================================

def processar_produtos_highlight(
    produtos,
    categoria_salva,
):
    """
    Processa o resultado de uma consulta de Highlights.

    Retorna:
        recebidos
        novos
        conhecidos_ou_recentes
        invalidos
        erros
    """

    recebidos = len(
        produtos
    )

    novos = 0
    conhecidos_ou_recentes = 0
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
            produto.get(
                "tipo"
            )
            or produto.get(
                "type"
            )
        )

        nome = (
            produto.get(
                "nome"
            )
            or produto.get(
                "name"
            )
            or produto.get(
                "title"
            )
        )

        if (
            not ml_id
            or not tipo
            or not nome
        ):
            invalidos += 1
            continue

        oportunidade = {
            "id":
                ml_id,

            "tipo":
                tipo,

            "nome":
                nome,

            "imagem": (
                produto.get(
                    "imagem"
                )
                or produto.get(
                    "picture"
                )
                or produto.get(
                    "thumbnail"
                )
            ),

            "ranking": (
                produto.get(
                    "ranking"
                )
                or produto.get(
                    "position"
                )
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
                # salvar_oportunidade() retorna False
                # tanto quando a oportunidade já existe
                # quanto quando foi publicada recentemente.
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
    total_conhecidos_ou_recentes = 0
    total_invalidos = 0
    total_erros = 0

    for (
        categoria_nome,
        categoria_id,
    ) in CATEGORIAS.items():

        print()
        print(
            "#" * 70
        )

        print(
            f"GRUPO: {categoria_nome}"
        )

        print(
            "#" * 70
        )

        categorias_coleta = (
            montar_categorias_coleta(
                highlights,
                categoria_nome,
                categoria_id,
            )
        )

        quantidade_subcategorias = (
            len(
                categorias_coleta
            )
            - 1
        )

        print(
            "Categoria principal: "
            f"{categoria_id}"
        )

        print(
            "Subcategorias selecionadas: "
            f"{quantidade_subcategorias}"
        )

        grupo_recebidos = 0
        grupo_novos = 0
        grupo_conhecidos = 0

        for categoria in categorias_coleta:
            total_consultas += 1

            prefixo = (
                "Principal"
                if categoria[
                    "principal"
                ]
                else "Subcategoria"
            )

            print()
            print(
                f"  [{prefixo}] "
                f"{categoria['nome_api']} "
                f"({categoria['id']})"
            )

            try:
                produtos = (
                    highlights.buscar(
                        categoria[
                            "id"
                        ]
                    )
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
                )
            )

            total_recebidos += (
                resultado[
                    "recebidos"
                ]
            )

            total_novos += (
                resultado[
                    "novos"
                ]
            )

            total_conhecidos_ou_recentes += (
                resultado[
                    "conhecidos_ou_recentes"
                ]
            )

            total_invalidos += (
                resultado[
                    "invalidos"
                ]
            )

            total_erros += (
                resultado[
                    "erros"
                ]
            )

            grupo_recebidos += (
                resultado[
                    "recebidos"
                ]
            )

            grupo_novos += (
                resultado[
                    "novos"
                ]
            )

            grupo_conhecidos += (
                resultado[
                    "conhecidos_ou_recentes"
                ]
            )

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

            if resultado[
                "invalidos"
            ]:
                print(
                    "    Inválidos: "
                    f"{resultado['invalidos']}"
                )

            if resultado[
                "erros"
            ]:
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
        f"{total_conhecidos_ou_recentes}"
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

        print(
            erro
        )

    try:
        coletar_highlights()

    except Exception as erro:
        print(
            "Erro geral nos highlights:"
        )

        print(
            erro
        )


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
        "Intervalo de coleta: "
        "1 hora"
    )

    print(
        "Expansão de subcategorias: "
        + (
            "ATIVA"
            if EXPANDIR_SUBCATEGORIAS
            else "DESATIVADA"
        )
    )

    if EXPANDIR_SUBCATEGORIAS:
        print(
            "Máximo de subcategorias "
            "por grupo: "
            f"{MAX_SUBCATEGORIAS_POR_GRUPO}"
        )

    while True:
        try:
            executar_coleta()

        except Exception as erro:
            print()
            print(
                "Erro inesperado "
                "no ciclo:"
            )

            print(
                erro
            )

        print()
        print(
            "Próxima coleta "
            "em 1 hora."
        )

        print()

        time.sleep(
            INTERVALO_SEGUNDOS
        )


if __name__ == "__main__":
    executar_worker()