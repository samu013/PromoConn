from database.database import conectar
from services.pontuacao import calcular_oportunidades
from telegram_bot.bot import enviar_produto


# =========================================================
# BUSCAR PRODUTO
# =========================================================

def buscar_produto(oportunidade_id):
    produtos = calcular_oportunidades(
        limite=None
    )

    for produto in produtos:
        if produto["id"] == oportunidade_id:
            return produto

    return None


# =========================================================
# EXTRAIR MESSAGE ID DO TELEGRAM
# =========================================================

def extrair_message_id(resposta):
    if not isinstance(resposta, dict):
        return None

    resultado = resposta.get(
        "result",
        {}
    )

    message_id = resultado.get(
        "message_id"
    )

    if message_id is None:
        return None

    return str(message_id)


# =========================================================
# MOVER PARA HISTÓRICO
# =========================================================

def mover_para_historico(
    produto,
    telegram_message_id=None
):
    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO historico_publicacoes (
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
                telegram_message_id,
                publicado_em
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
                %s,
                %s,
                %s,
                %s,
                CURRENT_TIMESTAMP
            )
            """,
            (
                produto["ml_id"],
                produto["tipo"],
                produto["nome"],
                produto["imagem"],
                produto["categoria"],
                produto["ranking"],
                produto["link_produto"],
                produto["link_afiliado"],
                produto["preco"],
                produto["preco_original"],
                produto["desconto"],
                telegram_message_id,
            )
        )

        # Remove da fila ativa somente depois
        # de inserir no histórico.

        cursor.execute(
            """
            DELETE FROM oportunidades
            WHERE id = %s
            """,
            (
                produto["id"],
            )
        )

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        cursor.close()
        conexao.close()


# =========================================================
# PUBLICAR UM PRODUTO ESPECÍFICO
# =========================================================

def publicar_produto_por_id(
    oportunidade_id
):
    produto = buscar_produto(
        oportunidade_id
    )

    if produto is None:
        return {
            "sucesso": False,
            "erro": "Produto não encontrado.",
        }

    if (
        produto.get("status")
        != "pronto_publicar"
    ):
        return {
            "sucesso": False,
            "erro": (
                "Produto ainda não está "
                "pronto para publicar."
            ),
        }

    if not produto.get(
        "link_afiliado"
    ):
        return {
            "sucesso": False,
            "erro": (
                "Produto sem link de afiliado."
            ),
        }

    if produto.get(
        "preco"
    ) is None:
        return {
            "sucesso": False,
            "erro": "Produto sem preço.",
        }

    # =====================================================
    # TELEGRAM
    # =====================================================

    try:
        resposta = enviar_produto(
            produto
        )

    except Exception as erro:
        return {
            "sucesso": False,
            "erro": (
                f"Erro ao enviar para "
                f"Telegram: {erro}"
            ),
        }

    telegram_message_id = (
        extrair_message_id(
            resposta
        )
    )

    # =====================================================
    # HISTÓRICO
    # =====================================================

    try:
        mover_para_historico(
            produto,
            telegram_message_id,
        )

    except Exception as erro:
        return {
            "sucesso": False,
            "erro": (
                "Mensagem enviada ao Telegram, "
                "mas ocorreu erro ao atualizar "
                f"o banco: {erro}"
            ),
        }

    return {
        "sucesso": True,
        "produto_id": produto["id"],
        "ml_id": produto["ml_id"],
        "nome": produto["nome"],
        "telegram_message_id":
            telegram_message_id,
    }


# =========================================================
# PUBLICAR PRÓXIMO DA FILA
# =========================================================

def publicar_proxima_promocao():
    """
    Procura todos os produtos prontos e publica
    somente UM: o de maior pontuação.

    Essa é a função que o agendador chamará
    de 5 em 5 minutos.
    """

    produtos = calcular_oportunidades(
        limite=None
    )

    fila = [
        produto
        for produto in produtos
        if (
            produto.get("status")
            == "pronto_publicar"
            and produto.get("link_afiliado")
            and produto.get("preco") is not None
        )
    ]

    if not fila:
        print(
            "📭 Nenhuma promoção pronta "
            "na fila."
        )

        return {
            "sucesso": False,
            "fila_vazia": True,
            "erro": (
                "Nenhuma promoção pronta "
                "para publicação."
            ),
        }

    # Maior score primeiro.
    fila.sort(
        key=lambda produto:
            produto.get(
                "pontuacao",
                0
            ),
        reverse=True,
    )

    produto = fila[0]

    print()
    print(
        "🚀 Próxima promoção:"
    )

    print(
        f"   {produto['nome']}"
    )

    print(
        f"   Score: "
        f"{produto['pontuacao']}"
    )

    resultado = (
        publicar_produto_por_id(
            produto["id"]
        )
    )

    if resultado["sucesso"]:
        print(
            "✅ Publicada com sucesso."
        )

    else:
        print(
            "❌ Falha:",
            resultado["erro"],
        )

    return resultado