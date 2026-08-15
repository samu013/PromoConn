from datetime import (
    datetime,
    timedelta,
    timezone,
)
from zoneinfo import ZoneInfo

from database.database import conectar


FUSO_BRASIL = ZoneInfo(
    "America/Sao_Paulo"
)


def _numero(
    valor,
    padrao=0.0,
):
    try:
        return float(
            valor
        )

    except (
        TypeError,
        ValueError,
    ):
        return padrao


def _data_local(
    valor
):
    if not valor:
        return None

    if isinstance(
        valor,
        datetime,
    ):
        data = valor

    else:
        try:
            data = (
                datetime.fromisoformat(
                    str(valor)
                )
            )

        except ValueError:
            return None

    # O projeto normalmente grava timestamps em UTC.
    # Se vier sem timezone, tratamos como UTC antes
    # de converter para horário de São Paulo.
    if data.tzinfo is None:
        data = data.replace(
            tzinfo=timezone.utc
        )

    return data.astimezone(
        FUSO_BRASIL
    )


def _calcular_desconto(
    produto
):
    desconto = _numero(
        produto.get(
            "desconto"
        ),
        None,
    )

    if desconto is not None:
        return max(
            0.0,
            desconto,
        )

    preco = _numero(
        produto.get(
            "preco"
        ),
        None,
    )

    preco_original = _numero(
        produto.get(
            "preco_original"
        ),
        None,
    )

    if (
        preco is None
        or preco_original is None
        or preco_original <= 0
        or preco_original <= preco
    ):
        return 0.0

    return round(
        (
            (
                preco_original
                - preco
            )
            / preco_original
        )
        * 100,
        2,
    )


def _calcular_score_instagram(
    produto
):
    desconto = _calcular_desconto(
        produto
    )

    ranking = produto.get(
        "ranking"
    )

    ranking_bonus = 0.0

    if ranking is not None:
        ranking_numero = _numero(
            ranking,
            9999,
        )

        # Ranking menor é melhor.
        ranking_bonus = max(
            0.0,
            30.0
            - min(
                ranking_numero,
                30.0,
            )
        )

    preco_original_bonus = (
        8.0
        if produto.get(
            "preco_original"
        )
        else 0.0
    )

    return round(
        (desconto * 2.0)
        + ranking_bonus
        + preco_original_bonus,
        2,
    )


def _buscar_publicacoes_recentes():
    conexao = conectar()
    cursor = conexao.cursor()

    try:
        # Buscamos 48 horas e filtramos a data local em Python.
        # Isso evita diferença de fuso entre Neon/Render e Brasil.
        cursor.execute(
            """
            SELECT
                id,
                ml_id,
                tipo,
                nome,
                imagem,
                categoria,
                ranking,
                link_produto,
                link_afiliado,
                preco,
                preco_original,
                desconto,
                telegram_canal,
                publicado_em

            FROM historico_publicacoes

            WHERE publicado_em >=
                CURRENT_TIMESTAMP
                - INTERVAL '48 hours'

            ORDER BY
                publicado_em DESC
            """
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        conexao.close()


def buscar_top_promocoes_do_dia(
    quantidade=5,
    max_por_categoria=2,
):
    agora = datetime.now(
        FUSO_BRASIL
    )

    hoje = agora.date()

    publicacoes = (
        _buscar_publicacoes_recentes()
    )

    publicados_hoje = []

    for produto in publicacoes:
        data_local = _data_local(
            produto.get(
                "publicado_em"
            )
        )

        if (
            data_local is None
            or data_local.date() != hoje
        ):
            continue

        item = dict(
            produto
        )

        item[
            "publicado_em_local"
        ] = data_local

        publicados_hoje.append(
            item
        )

    candidatos = []
    ids_vistos = set()

    for produto in publicados_hoje:
        ml_id = str(
            produto.get(
                "ml_id",
                "",
            )
        ).strip()

        if (
            not ml_id
            or ml_id in ids_vistos
        ):
            continue

        if not produto.get(
            "imagem"
        ):
            continue

        preco = _numero(
            produto.get(
                "preco"
            ),
            None,
        )

        if (
            preco is None
            or preco <= 0
        ):
            continue

        ids_vistos.add(
            ml_id
        )

        produto[
            "desconto_instagram"
        ] = _calcular_desconto(
            produto
        )

        produto[
            "score_instagram"
        ] = _calcular_score_instagram(
            produto
        )

        candidatos.append(
            produto
        )

    candidatos.sort(
        key=lambda item: (
            item.get(
                "score_instagram",
                0
            ),
            item.get(
                "desconto_instagram",
                0
            ),
            item.get(
                "publicado_em_local"
            ),
        ),
        reverse=True,
    )

    selecionados = []
    categorias = {}
    selecionados_ids = set()

    # Primeira passagem: prioriza variedade.
    for produto in candidatos:
        categoria = (
            produto.get(
                "categoria"
            )
            or "Geral"
        )

        quantidade_categoria = (
            categorias.get(
                categoria,
                0,
            )
        )

        if (
            quantidade_categoria
            >= max_por_categoria
        ):
            continue

        selecionados.append(
            produto
        )

        selecionados_ids.add(
            produto["ml_id"]
        )

        categorias[
            categoria
        ] = (
            quantidade_categoria
            + 1
        )

        if len(
            selecionados
        ) >= quantidade:
            break

    # Se a variedade impedir completar 5, completa
    # com os melhores restantes.
    if len(
        selecionados
    ) < quantidade:
        for produto in candidatos:
            if (
                produto["ml_id"]
                in selecionados_ids
            ):
                continue

            selecionados.append(
                produto
            )

            selecionados_ids.add(
                produto["ml_id"]
            )

            if len(
                selecionados
            ) >= quantidade:
                break

    return {
        "produtos": selecionados,

        "total_publicados_hoje":
            len(
                publicados_hoje
            ),

        "total_candidatos":
            len(
                candidatos
            ),

        "data_referencia":
            agora.strftime(
                "%d/%m/%Y"
            ),
    }
