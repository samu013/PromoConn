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


CATEGORIAS = {
    "Celulares": "MLB1055",
    "Games": "MLB1144",
    "Tecnologia": "MLB1648",
    "Casa": "MLB1574",
    "Esportes": "MLB264201",
}


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
        start=1
    ):
        # Permite alguns formatos diferentes.
        if isinstance(tendencia, str):
            palavra = tendencia
            url = None
            posicao_api = posicao

        elif isinstance(tendencia, dict):
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
# HIGHLIGHTS
# =========================================================

def coletar_highlights():
    print()
    print("=" * 70)
    print("COLETANDO HIGHLIGHTS")
    print("=" * 70)

    highlights = Highlights()

    total_recebidos = 0
    total_novos = 0


    for categoria_nome, categoria_id in (
        CATEGORIAS.items()
    ):
        print()
        print(
            f"Categoria: {categoria_nome}"
        )

        try:
            produtos = highlights.buscar(
                categoria_id
            )

        except Exception as erro:
            print(
                f"Erro ao buscar "
                f"{categoria_nome}: {erro}"
            )
            continue


        if not produtos:
            print(
                "Nenhum produto retornado."
            )
            continue


        print(
            f"Produtos recebidos: "
            f"{len(produtos)}"
        )

        total_recebidos += len(
            produtos
        )


        for produto in produtos:
            if not isinstance(
                produto,
                dict
            ):
                continue

            # A função salvar_oportunidade()
            # espera pelo menos:
            #
            # id
            # tipo
            # nome
            #
            # então validamos antes.

            ml_id = produto.get("id")

            tipo = (
                produto.get("tipo")
                or produto.get("type")
            )

            nome = (
                produto.get("nome")
                or produto.get("name")
                or produto.get("title")
            )

            if not ml_id:
                continue

            if not tipo:
                continue

            if not nome:
                continue


            oportunidade = {
                "id": ml_id,
                "tipo": tipo,
                "nome": nome,
                "imagem": (
                    produto.get("imagem")
                    or produto.get("picture")
                    or produto.get(
                        "thumbnail"
                    )
                ),
                "ranking": (
                    produto.get("ranking")
                    or produto.get(
                        "position"
                    )
                ),
            }


            try:
                novo = salvar_oportunidade(
                    produto=oportunidade,
                    fonte="highlights",
                    categoria=categoria_nome,
                )

                if novo:
                    total_novos += 1

            except Exception as erro:
                print(
                    f"Erro ao salvar "
                    f"{ml_id}: {erro}"
                )


    print()
    print(
        f"Highlights recebidos: "
        f"{total_recebidos}"
    )

    print(
        f"Novas oportunidades: "
        f"{total_novos}"
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
        "Intervalo de coleta: "
        "1 hora"
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
            print(erro)


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