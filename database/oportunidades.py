from datetime import datetime, timedelta

from database.database import conectar


DIAS_PARA_REPUBLICAR = 7


def foi_publicado_recentemente(
    ml_id,
    dias=DIAS_PARA_REPUBLICAR
):
    conexao = conectar()
    cursor = conexao.cursor()

    data_limite = (
        datetime.now()
        - timedelta(days=dias)
    )

    cursor.execute(
        """
        SELECT id
        FROM historico_publicacoes

        WHERE ml_id = %s
          AND publicado_em >= %s

        LIMIT 1
        """,
        (
            ml_id,
            data_limite,
        )
    )

    encontrado = (
        cursor.fetchone()
        is not None
    )

    cursor.close()
    conexao.close()

    return encontrado


def salvar_oportunidade(
    produto,
    fonte="highlights",
    categoria=None
):
    """
    Salva ou atualiza uma oportunidade.

    Retorna:
        True  -> oportunidade nova
        False -> já existia ou foi publicada recentemente
    """

    ml_id = produto["id"]

    # =====================================================
    # NÃO REPUBLICAR MUITO CEDO
    # =====================================================

    if foi_publicado_recentemente(
        ml_id
    ):
        return False

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        # =================================================
        # VERIFICA SE JÁ EXISTE NA FILA
        # =================================================

        cursor.execute(
            """
            SELECT id
            FROM oportunidades

            WHERE ml_id = %s
            """,
            (ml_id,)
        )

        existente = cursor.fetchone()

        # =================================================
        # ATUALIZA
        # =================================================

        if existente:

            cursor.execute(
                """
                UPDATE oportunidades

                SET
                    tipo = %s,
                    nome = %s,
                    imagem = %s,
                    fonte = %s,
                    ranking = %s,
                    categoria = %s,
                    atualizado_em =
                        CURRENT_TIMESTAMP

                WHERE ml_id = %s
                """,
                (
                    produto["tipo"],
                    produto["nome"],
                    produto.get("imagem"),
                    fonte,
                    produto.get("ranking"),
                    categoria,
                    ml_id,
                )
            )

            novo = False

        # =================================================
        # INSERE
        # =================================================

        else:

            cursor.execute(
                """
                INSERT INTO oportunidades (
                    ml_id,
                    tipo,
                    nome,
                    imagem,
                    fonte,
                    ranking,
                    categoria,
                    status,
                    descoberto_em,
                    atualizado_em
                )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    'aguardando_link',
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                """,
                (
                    ml_id,
                    produto["tipo"],
                    produto["nome"],
                    produto.get("imagem"),
                    fonte,
                    produto.get("ranking"),
                    categoria,
                )
            )

            novo = True

        conexao.commit()

        return novo

    except Exception:
        conexao.rollback()
        raise

    finally:
        cursor.close()
        conexao.close()


def buscar_oportunidade_por_id(
    oportunidade_id
):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT *
        FROM oportunidades

        WHERE id = %s
        """,
        (oportunidade_id,)
    )

    oportunidade = cursor.fetchone()

    cursor.close()
    conexao.close()

    return oportunidade


def excluir_oportunidade(
    oportunidade_id
):
    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            DELETE FROM oportunidades
            WHERE id = %s
            """,
            (oportunidade_id,)
        )

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        cursor.close()
        conexao.close()


def contar_oportunidades():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM oportunidades
    """)

    resultado = cursor.fetchone()

    cursor.close()
    conexao.close()

    return resultado["total"]