from datetime import datetime, timedelta

from database.database import conectar


DIAS_PARA_REPUBLICAR = 7


def normalizar_origem(origem):
    origem = str(origem or "mercadolivre").strip().lower()
    aliases = {
        "mercado_livre": "mercadolivre",
        "mercado livre": "mercadolivre",
        "ml": "mercadolivre",
        "meli": "mercadolivre",
        "shein": "shein",
    }
    return aliases.get(origem, origem)


def foi_publicado_recentemente(ml_id, dias=DIAS_PARA_REPUBLICAR, origem="mercadolivre"):
    origem = normalizar_origem(origem)
    data_limite = datetime.now() - timedelta(days=dias)
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute(
            """
            SELECT id FROM historico_publicacoes
            WHERE ml_id = %s AND origem = %s AND publicado_em >= %s
            LIMIT 1
            """,
            (str(ml_id), origem, data_limite),
        )
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conexao.close()


def salvar_oportunidade(produto, fonte="highlights", categoria=None, origem="mercadolivre"):
    origem = normalizar_origem(origem)
    produto_id = str(produto["id"])

    if foi_publicado_recentemente(produto_id, origem=origem):
        return False

    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute(
            """
            SELECT id, categoria FROM oportunidades
            WHERE ml_id = %s AND origem = %s
            LIMIT 1
            """,
            (produto_id, origem),
        )
        existente = cursor.fetchone()

        if existente:
            cursor.execute(
                """
                UPDATE oportunidades
                SET tipo = %s,
                    nome = %s,
                    imagem = %s,
                    fonte = %s,
                    ranking = %s,
                    categoria = COALESCE(%s, categoria),
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE ml_id = %s AND origem = %s
                """,
                (
                    produto["tipo"], produto["nome"], produto.get("imagem"),
                    fonte, produto.get("ranking"), categoria, produto_id, origem,
                ),
            )
            novo = False
        else:
            cursor.execute(
                """
                INSERT INTO oportunidades (
                    ml_id, origem, tipo, nome, imagem, fonte, ranking,
                    categoria, status, descoberto_em, atualizado_em
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    'aguardando_link', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """,
                (
                    produto_id, origem, produto["tipo"], produto["nome"],
                    produto.get("imagem"), fonte, produto.get("ranking"), categoria,
                ),
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


def buscar_oportunidade_por_id(oportunidade_id):
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute("SELECT * FROM oportunidades WHERE id = %s", (oportunidade_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conexao.close()


def excluir_oportunidade(oportunidade_id):
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute("DELETE FROM oportunidades WHERE id = %s", (oportunidade_id,))
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        cursor.close()
        conexao.close()


def contar_oportunidades(origem=None):
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        if origem:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM oportunidades WHERE origem = %s",
                (normalizar_origem(origem),),
            )
        else:
            cursor.execute("SELECT COUNT(*) AS total FROM oportunidades")
        resultado = cursor.fetchone()
        return resultado["total"]
    finally:
        cursor.close()
        conexao.close()
