import math
import os
import threading
import hmac

from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    url_for,
)

from database.database import (
    conectar,
    criar_tabelas,
)

from services.pontuacao import (
    calcular_oportunidades,
)

from services.publicador import (
    publicar_produto_por_id,
    publicar_proxima_promocao,
)

from coletor_worker import (
    executar_coleta,
)


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)


ITENS_POR_PAGINA = 20


# =========================================================
# CRON
# =========================================================

CRON_SECRET = os.getenv(
    "CRON_SECRET"
)


# Evita iniciar duas coletas ao mesmo tempo
_lock_coleta = threading.Lock()


# Evita duas publicações simultâneas
_lock_publicacao = threading.Lock()


# =========================================================
# BANCO
# =========================================================

# Importante:
# gunicorn app:app não executa o bloco
# if __name__ == "__main__".
#
# Por isso verificamos as tabelas aqui.
criar_tabelas()


# =========================================================
# AUXILIARES
# =========================================================

def converter_preco(texto):
    if not texto:
        return None

    texto = (
        texto
        .replace("R$", "")
        .strip()
    )

    # Exemplo:
    #
    # R$ 1.299,90
    # ↓
    # 1299.90

    if "," in texto:
        texto = (
            texto
            .replace(".", "")
            .replace(",", ".")
        )

    return float(texto)


def filtrar_produtos(
    produtos,
    busca,
    categoria,
    status,
    ordem,
):
    resultado = list(
        produtos
    )

    # =====================================================
    # PESQUISA
    # =====================================================

    if busca:
        termo = busca.lower()

        resultado = [
            produto
            for produto in resultado

            if termo
            in produto.get(
                "nome",
                ""
            ).lower()
        ]

    # =====================================================
    # CATEGORIA
    # =====================================================

    if categoria:
        resultado = [
            produto
            for produto in resultado

            if produto.get(
                "categoria"
            )
            == categoria
        ]

    # =====================================================
    # STATUS
    # =====================================================

    if status:
        resultado = [
            produto
            for produto in resultado

            if produto.get(
                "status"
            )
            == status
        ]

    # =====================================================
    # ORDENAÇÃO
    # =====================================================

    if ordem == "ranking":

        resultado.sort(
            key=lambda produto: (
                produto.get(
                    "ranking"
                )

                if produto.get(
                    "ranking"
                )
                is not None

                else 999999
            )
        )

    elif ordem == "nome":

        resultado.sort(
            key=lambda produto:
                produto.get(
                    "nome",
                    ""
                ).lower()
        )

    else:

        # Maior score primeiro
        resultado.sort(
            key=lambda produto:
                produto.get(
                    "pontuacao",
                    0
                ),

            reverse=True,
        )

    return resultado


# =========================================================
# SEGURANÇA DO CRON
# =========================================================

def validar_cron():
    """
    Valida o header enviado pelo cron-job.org.

    Header esperado:

    X-Cron-Secret: SUA_CHAVE
    """

    if not CRON_SECRET:
        print(
            "ERRO: CRON_SECRET "
            "não configurado."
        )

        abort(500)

    token_recebido = (
        request.headers.get(
            "X-Cron-Secret",
            ""
        )
    )

    if not hmac.compare_digest(
        token_recebido,
        CRON_SECRET,
    ):
        abort(401)


# =========================================================
# PAINEL
# =========================================================

@app.route("/")
def painel():
    todos_produtos = (
        calcular_oportunidades(
            limite=None
        )
    )

    # =====================================================
    # FILTROS RECEBIDOS
    # =====================================================

    busca = request.args.get(
        "busca",
        ""
    ).strip()

    categoria = request.args.get(
        "categoria",
        ""
    ).strip()

    status = request.args.get(
        "status",
        ""
    ).strip()

    ordem = request.args.get(
        "ordem",
        "score"
    ).strip()

    try:
        pagina = int(
            request.args.get(
                "pagina",
                1
            )
        )

    except ValueError:
        pagina = 1

    pagina = max(
        pagina,
        1
    )

    # =====================================================
    # MÉTRICAS
    # =====================================================

    total_oportunidades = len(
        todos_produtos
    )

    total_aguardando = sum(
        1
        for produto in todos_produtos

        if produto.get(
            "status"
        )
        == "aguardando_link"
    )

    total_prontos = sum(
        1
        for produto in todos_produtos

        if produto.get(
            "status"
        )
        == "pronto_publicar"
    )

    # =====================================================
    # TOTAL PUBLICADOS
    # =====================================================

    conexao = conectar()
    cursor = conexao.cursor()

    try:

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM historico_publicacoes
            """
        )

        resultado = cursor.fetchone()

        total_publicados = (
            resultado["total"]
        )

    finally:

        cursor.close()
        conexao.close()

    # =====================================================
    # CATEGORIAS
    # =====================================================

    categorias = sorted(
        {
            produto["categoria"]

            for produto in todos_produtos

            if produto.get(
                "categoria"
            )
        }
    )

    # =====================================================
    # APLICA FILTROS
    # =====================================================

    produtos_filtrados = (
        filtrar_produtos(
            produtos=todos_produtos,
            busca=busca,
            categoria=categoria,
            status=status,
            ordem=ordem,
        )
    )

    total_filtrado = len(
        produtos_filtrados
    )

    # =====================================================
    # PAGINAÇÃO
    # =====================================================

    total_paginas = max(
        1,
        math.ceil(
            total_filtrado
            / ITENS_POR_PAGINA
        )
    )

    if pagina > total_paginas:
        pagina = total_paginas

    inicio = (
        (pagina - 1)
        * ITENS_POR_PAGINA
    )

    fim = (
        inicio
        + ITENS_POR_PAGINA
    )

    produtos = (
        produtos_filtrados[
            inicio:fim
        ]
    )

    # =====================================================
    # TEMPLATE
    # =====================================================

    return render_template(
        "painel.html",

        produtos=produtos,

        categorias=categorias,

        busca=busca,

        categoria_selecionada=
            categoria,

        status_selecionado=
            status,

        ordem_selecionada=
            ordem,

        pagina=pagina,

        total_paginas=
            total_paginas,

        total_filtrado=
            total_filtrado,

        total_oportunidades=
            total_oportunidades,

        total_aguardando=
            total_aguardando,

        total_prontos=
            total_prontos,

        total_publicados=
            total_publicados,
    )


# =========================================================
# SALVAR OFERTA
# =========================================================

@app.route(
    "/oportunidade/"
    "<int:oportunidade_id>/oferta",

    methods=["POST"],
)
def salvar_oferta(
    oportunidade_id
):
    link_produto = (
        request.form.get(
            "link_produto",
            ""
        ).strip()
    )

    link_afiliado = (
        request.form.get(
            "link_afiliado",
            ""
        ).strip()
    )

    preco_texto = (
        request.form.get(
            "preco",
            ""
        ).strip()
    )

    preco_original_texto = (
        request.form.get(
            "preco_original",
            ""
        ).strip()
    )

    # =====================================================
    # LINK DO PRODUTO
    # =====================================================

    if not link_produto.startswith(
        (
            "https://www.mercadolivre.com.br/",
            "https://produto.mercadolivre.com.br/",
        )
    ):
        return (
            "Link do produto inválido.",
            400
        )

    # =====================================================
    # LINK AFILIADO
    # =====================================================

    if not link_afiliado.startswith(
        (
            "https://meli.la/",
            "https://www.mercadolivre.com.br/social/",
        )
    ):
        return (
            "Link de afiliado inválido.",
            400
        )

    # =====================================================
    # PREÇO ATUAL
    # =====================================================

    try:

        preco = converter_preco(
            preco_texto
        )

    except ValueError:

        return (
            "Preço atual inválido.",
            400
        )

    if (
        preco is None
        or preco <= 0
    ):
        return (
            "Preço atual inválido.",
            400
        )

    # =====================================================
    # PREÇO ANTERIOR
    # =====================================================

    preco_original = None

    if preco_original_texto:

        try:

            preco_original = (
                converter_preco(
                    preco_original_texto
                )
            )

        except ValueError:

            return (
                "Preço anterior inválido.",
                400
            )

        if preco_original <= 0:

            return (
                "Preço anterior inválido.",
                400
            )

        if preco_original <= preco:

            return (
                "O preço anterior deve "
                "ser maior que o preço atual.",
                400
            )

    # =====================================================
    # DESCONTO
    # =====================================================

    desconto = None

    if preco_original is not None:

        desconto = round(
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

    # =====================================================
    # BANCO
    # =====================================================

    conexao = conectar()
    cursor = conexao.cursor()

    try:

        cursor.execute(
            """
            UPDATE oportunidades

            SET
                link_produto = %s,
                preco = %s,
                preco_original = %s,
                desconto = %s,
                link_afiliado = %s,
                status = 'pronto_publicar',
                atualizado_em =
                    CURRENT_TIMESTAMP

            WHERE id = %s
            """,

            (
                link_produto,
                preco,
                preco_original,
                desconto,
                link_afiliado,
                oportunidade_id,
            )
        )

        conexao.commit()

    except Exception:

        conexao.rollback()
        raise

    finally:

        cursor.close()
        conexao.close()

    return redirect(
        url_for(
            "painel"
        )
    )


# =========================================================
# PUBLICAÇÃO MANUAL
# =========================================================

@app.route(
    "/oportunidade/"
    "<int:oportunidade_id>/telegram",

    methods=["POST"],
)
def publicar_telegram(
    oportunidade_id
):
    resultado = (
        publicar_produto_por_id(
            oportunidade_id
        )
    )

    if not resultado.get(
        "sucesso"
    ):
        return (
            resultado.get(
                "erro",
                "Não foi possível publicar."
            ),
            400
        )

    return redirect(
        url_for(
            "painel"
        )
    )


# =========================================================
# CRON — PUBLICAÇÃO
# =========================================================

@app.route(
    "/tarefas/publicar",
    methods=["POST"],
)
def tarefa_publicar():
    """
    Chamado pelo cron-job.org
    aproximadamente a cada 5 minutos.

    Publica no máximo uma promoção.
    """

    validar_cron()

    # Evita duas publicações simultâneas
    if not _lock_publicacao.acquire(
        blocking=False
    ):
        return {
            "ok": True,
            "status": "ocupado",
            "mensagem": (
                "Já existe uma publicação "
                "em andamento."
            ),
        }

    try:

        print()
        print("=" * 70)
        print(
            "CRON - PUBLICAÇÃO AUTOMÁTICA"
        )
        print("=" * 70)

        resultado = (
            publicar_proxima_promocao()
        )

        if resultado.get(
            "sucesso"
        ):

            return {
                "ok": True,

                "status":
                    "publicado",

                "produto":
                    resultado.get(
                        "nome"
                    ),

                "canal":
                    resultado.get(
                        "telegram_canal"
                    ),
            }

        if resultado.get(
            "fila_vazia"
        ):

            return {
                "ok": True,

                "status":
                    "fila_vazia",

                "mensagem":
                    "Nenhuma promoção pronta.",
            }

        return {
            "ok": False,

            "status":
                "erro",

            "erro":
                resultado.get(
                    "erro",
                    "Erro desconhecido."
                ),
        }

    except Exception as erro:

        print(
            "Erro no cron de publicação:"
        )

        print(erro)

        return {
            "ok": False,
            "status": "erro",
            "erro": str(erro),
        }, 500

    finally:

        _lock_publicacao.release()


# =========================================================
# CRON — COLETA
# =========================================================

def _executar_coleta_background():
    """
    Executa a coleta em segundo plano.

    A rota HTTP pode responder rapidamente
    ao cron-job.org enquanto a coleta continua.
    """

    try:

        print()
        print("=" * 70)
        print(
            "CRON - COLETA AUTOMÁTICA"
        )
        print("=" * 70)

        executar_coleta()

        print()
        print(
            "Coleta automática finalizada."
        )

    except Exception as erro:

        print()
        print(
            "Erro na coleta automática:"
        )

        print(erro)

    finally:

        _lock_coleta.release()


@app.route(
    "/tarefas/coletar",
    methods=["POST"],
)
def tarefa_coletar():
    """
    Chamado pelo cron-job.org
    aproximadamente uma vez por hora.
    """

    validar_cron()

    # Já existe uma coleta em andamento?
    if not _lock_coleta.acquire(
        blocking=False
    ):

        return {
            "ok": True,

            "status":
                "ocupado",

            "mensagem":
                "Já existe uma coleta em andamento.",
        }

    try:

        thread = threading.Thread(
            target=
                _executar_coleta_background,

            daemon=True,

            name=
                "PromoConnColeta",
        )

        thread.start()

    except Exception:

        _lock_coleta.release()
        raise

    return {
        "ok": True,

        "status":
            "iniciado",

        "mensagem":
            "Coleta iniciada em segundo plano.",
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route(
    "/health",
    methods=["GET"],
)
def health():
    """
    Rota simples para conferir se o
    Web Service está vivo.
    """

    return {
        "ok": True,
        "servico": "PromoConn",
    }


# =========================================================
# EXECUÇÃO LOCAL
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000,
    )