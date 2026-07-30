from datetime import datetime, timedelta

from database.database import conectar


DIAS_PARA_REPUBLICAR = 7


def normalizar_origem(origem):
    origem = str(
        origem or "mercadolivre"
    ).strip().lower()

    aliases = {
        "mercado_livre": "mercadolivre",
        "mercado livre": "mercadolivre",
        "ml": "mercadolivre",
        "meli": "mercadolivre",
    }

    return aliases.get(origem, origem)


def foi_publicado_recentemente(
    ml_id,
    dias=DIAS_PARA_REPUBLICAR,
    origem="mercadolivre",
):
    origem = normalizar_origem(origem)
    data_limite = datetime.now() - timedelta(days=dias)

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM historico_publicacoes
            WHERE ml_id = %s
              AND origem = %s
              AND publicado_em >= %s
            LIMIT 1
            """,
            (
                str(ml_id),
                origem,
                data_limite,
            ),
        )

        return cursor.fetchone() is not None

    finally:
        cursor.close()
        conexao.close()


def salvar_oportunidade(
    produto,
    fonte="highlights",
    categoria=None,
    origem="mercadolivre",
):
    origem = normalizar_origem(origem)
    produto_id = str(produto["id"])

    if foi_publicado_recentemente(
        produto_id,
        origem=origem,
    ):
        return False

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO oportunidades (
                ml_id,
                origem,
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
                %s,
                'aguardando_link',
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (origem, ml_id)
            DO UPDATE SET
                tipo = EXCLUDED.tipo,
                nome = EXCLUDED.nome,
                imagem = COALESCE(
                    EXCLUDED.imagem,
                    oportunidades.imagem
                ),
                fonte = EXCLUDED.fonte,
                ranking = EXCLUDED.ranking,
                categoria = COALESCE(
                    EXCLUDED.categoria,
                    oportunidades.categoria
                ),
                atualizado_em = CURRENT_TIMESTAMP
            RETURNING
                (xmax = 0) AS inserido
            """,
            (
                produto_id,
                origem,
                produto.get("tipo"),
                produto.get("nome"),
                produto.get("imagem"),
                fonte,
                produto.get("ranking"),
                categoria,
            ),
        )

        resultado = cursor.fetchone()
        conexao.commit()

        return bool(resultado and resultado["inserido"])

    except Exception:
        conexao.rollback()
        raise

    finally:
        cursor.close()
        conexao.close()
