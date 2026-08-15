import hmac
import math
import os
import threading
from datetime import timedelta
from functools import wraps
from urllib.parse import urlsplit

from dotenv import load_dotenv

from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from flask_wtf.csrf import (
    CSRFError,
    CSRFProtect,
)

from werkzeug.security import (
    check_password_hash,
)

from coletor_worker import executar_coleta

from database.canais_telegram import (
    listar_canais,
)

from database.database import (
    conectar,
    criar_tabelas,
)

from database.oportunidades import (
    excluir_oportunidade,
)

from services.pontuacao import (
    calcular_oportunidades,
)

from services.publicador import (
    publicar_produto_por_id,
    publicar_proxima_promocao,
)

from services.instagram.seletor import (
    buscar_top_promocoes_do_dia,
)

from services.instagram.gerador_artes import (
    gerar_artes_top,
    listar_artes_do_dia,
)


# =========================================================
# ENV
# =========================================================

load_dotenv()


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)

ITENS_POR_PAGINA = 20


# =========================================================
# SEGREDOS / CONFIGURAÇÃO
# =========================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY"
)

ADMIN_USER = os.getenv(
    "ADMIN_USER"
)

ADMIN_PASSWORD_HASH = os.getenv(
    "ADMIN_PASSWORD_HASH"
)

CRON_SECRET = os.getenv(
    "CRON_SECRET"
)


if not SECRET_KEY:
    raise ValueError(
        "SECRET_KEY não encontrada no ambiente."
    )

if not ADMIN_USER:
    raise ValueError(
        "ADMIN_USER não encontrada no ambiente."
    )

if not ADMIN_PASSWORD_HASH:
    raise ValueError(
        "ADMIN_PASSWORD_HASH não encontrada no ambiente."
    )


app.config.update(
    SECRET_KEY=SECRET_KEY,

    SESSION_COOKIE_HTTPONLY=True,

    # No Render o site usa HTTPS.
    # Para desenvolvimento local em http://127.0.0.1,
    # deixamos False quando FLASK_ENV=development.
    SESSION_COOKIE_SECURE=(
        os.getenv(
            "FLASK_ENV",
            "production"
        ).lower()
        != "development"
    ),

    SESSION_COOKIE_SAMESITE="Lax",

    PERMANENT_SESSION_LIFETIME=
        timedelta(
            hours=8
        ),

    WTF_CSRF_TIME_LIMIT=8 * 60 * 60,
)


csrf = CSRFProtect(
    app
)


# =========================================================
# LOCKS
# =========================================================

_lock_coleta = threading.Lock()
_lock_publicacao = threading.Lock()


# =========================================================
# BANCO
# =========================================================

criar_tabelas()


# =========================================================
# AUTENTICAÇÃO
# =========================================================

def esta_logado():
    return bool(
        session.get(
            "autenticado"
        )
    )


def login_obrigatorio(
    funcao
):
    @wraps(funcao)
    def wrapper(
        *args,
        **kwargs
    ):
        if not esta_logado():
            return redirect(
                url_for(
                    "login",
                    next=request.full_path,
                )
            )

        return funcao(
            *args,
            **kwargs
        )

    return wrapper


def destino_seguro(
    destino
):
    """
    Impede redirecionamento para domínio externo
    após o login.
    """

    if not destino:
        return None

    partes = urlsplit(
        destino
    )

    if partes.scheme or partes.netloc:
        return None

    if not destino.startswith("/"):
        return None

    return destino


@app.route(
    "/login",
    methods=[
        "GET",
        "POST",
    ],
)
def login():
    if esta_logado():
        return redirect(
            url_for(
                "painel"
            )
        )

    erro = None

    if request.method == "POST":
        usuario = (
            request.form.get(
                "usuario",
                ""
            ).strip()
        )

        senha = (
            request.form.get(
                "senha",
                ""
            )
        )

        usuario_correto = (
            hmac.compare_digest(
                usuario,
                ADMIN_USER
            )
        )

        senha_correta = (
            check_password_hash(
                ADMIN_PASSWORD_HASH,
                senha,
            )
        )

        if (
            usuario_correto
            and senha_correta
        ):
            session.clear()

            session[
                "autenticado"
            ] = True

            session[
                "usuario"
            ] = ADMIN_USER

            session.permanent = True

            destino = (
                destino_seguro(
                    request.form.get(
                        "next"
                    )
                )
            )

            return redirect(
                destino
                or url_for(
                    "painel"
                )
            )

        erro = (
            "Usuário ou senha inválidos."
        )

    return render_template(
        "login.html",
        erro=erro,
        next_url=(
            destino_seguro(
                request.args.get(
                    "next"
                )
            )
            or ""
        ),
    )


@app.route(
    "/sair",
    methods=["POST"],
)
@login_obrigatorio
def sair():
    session.clear()

    return redirect(
        url_for(
            "login"
        )
    )


# =========================================================
# AUXILIARES
# =========================================================

def converter_preco(
    texto
):
    if not texto:
        return None

    texto = (
        texto
        .replace(
            "R$",
            ""
        )
        .strip()
    )

    if "," in texto:
        texto = (
            texto
            .replace(
                ".",
                ""
            )
            .replace(
                ",",
                "."
            )
        )

    return float(
        texto
    )


def filtrar_produtos(
    produtos,
    busca="",
    categoria="",
    status="",
    ordem="score",
):
    resultado = list(
        produtos
    )

    if busca:
        termo = (
            busca.lower()
        )

        resultado = [
            produto
            for produto
            in resultado

            if termo
            in produto.get(
                "nome",
                ""
            ).lower()
        ]

    if categoria:
        resultado = [
            produto
            for produto
            in resultado

            if produto.get(
                "categoria"
            )
            == categoria
        ]

    if status:
        resultado = [
            produto
            for produto
            in resultado

            if produto.get(
                "status"
            )
            == status
        ]

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
        resultado.sort(
            key=lambda produto:
                produto.get(
                    "pontuacao",
                    0
                ),
            reverse=True,
        )

    return resultado


def paginar_lista(
    itens,
    pagina,
    por_pagina=
        ITENS_POR_PAGINA,
):
    total_itens = len(
        itens
    )

    total_paginas = max(
        1,

        math.ceil(
            total_itens
            / por_pagina
        )
    )

    pagina = max(
        1,

        min(
            pagina,
            total_paginas
        )
    )

    inicio = (
        (pagina - 1)
        * por_pagina
    )

    fim = (
        inicio
        + por_pagina
    )

    return (
        itens[
            inicio:fim
        ],

        pagina,

        total_paginas,

        total_itens,
    )


def obter_metricas(
    produtos=None
):
    if produtos is None:
        produtos = (
            calcular_oportunidades(
                limite=None
            )
        )

    total_oportunidades = len(
        produtos
    )

    total_aguardando = sum(
        1
        for produto
        in produtos

        if produto.get(
            "status"
        )
        == "aguardando_link"
    )

    total_prontos = sum(
        1
        for produto
        in produtos

        if produto.get(
            "status"
        )
        == "pronto_publicar"
    )

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM historico_publicacoes
            """
        )

        resultado = (
            cursor.fetchone()
        )

        total_publicados = (
            resultado["total"]
        )

    finally:
        cursor.close()
        conexao.close()

    return {
        "total_oportunidades":
            total_oportunidades,

        "total_aguardando":
            total_aguardando,

        "total_prontos":
            total_prontos,

        "total_publicados":
            total_publicados,
    }


# =========================================================
# SEGURANÇA DO CRON
# =========================================================

def validar_cron():
    if not CRON_SECRET:
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
# DASHBOARD
# =========================================================

@app.route("/")
@login_obrigatorio
def painel():
    todos_produtos = (
        calcular_oportunidades(
            limite=None
        )
    )

    metricas = obter_metricas(
        todos_produtos
    )

    fila_publicacao = [
        produto
        for produto
        in todos_produtos

        if produto.get(
            "status"
        )
        == "pronto_publicar"
    ]

    fila_publicacao.sort(
        key=lambda produto:
            produto.get(
                "pontuacao",
                0
            ),
        reverse=True,
    )

    busca = (
        request.args.get(
            "busca",
            ""
        ).strip()
    )

    categoria = (
        request.args.get(
            "categoria",
            ""
        ).strip()
    )

    status = (
        request.args.get(
            "status",
            ""
        ).strip()
    )

    ordem = (
        request.args.get(
            "ordem",
            "score"
        ).strip()
    )

    try:
        pagina = int(
            request.args.get(
                "pagina",
                1
            )
        )

    except ValueError:
        pagina = 1

    categorias = sorted(
        {
            produto[
                "categoria"
            ]

            for produto
            in todos_produtos

            if produto.get(
                "categoria"
            )
        }
    )

    produtos_filtrados = (
        filtrar_produtos(
            todos_produtos,

            busca=busca,

            categoria=
                categoria,

            status=status,

            ordem=ordem,
        )
    )

    (
        produtos,
        pagina,
        total_paginas,
        total_filtrado,
    ) = paginar_lista(
        produtos_filtrados,
        pagina,
    )

    return render_template(
        "painel.html",

        pagina_ativa=
            "dashboard",

        produtos=produtos,

        fila_publicacao=
            fila_publicacao,

        categorias=
            categorias,

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

        **metricas,
    )


# =========================================================
# AGUARDANDO LINK
# =========================================================

@app.route(
    "/link"
)
@login_obrigatorio
def pagina_link():
    todos_produtos = (
        calcular_oportunidades(
            limite=None
        )
    )

    metricas = obter_metricas(
        todos_produtos
    )

    aguardando = [
        produto
        for produto
        in todos_produtos

        if produto.get(
            "status"
        )
        == "aguardando_link"
    ]

    busca = (
        request.args.get(
            "busca",
            ""
        ).strip()
    )

    categoria = (
        request.args.get(
            "categoria",
            ""
        ).strip()
    )

    ordem = (
        request.args.get(
            "ordem",
            "score"
        ).strip()
    )

    try:
        pagina = int(
            request.args.get(
                "pagina",
                1
            )
        )

    except ValueError:
        pagina = 1

    categorias = sorted(
        {
            produto[
                "categoria"
            ]

            for produto
            in aguardando

            if produto.get(
                "categoria"
            )
        }
    )

    produtos_filtrados = (
        filtrar_produtos(
            aguardando,

            busca=busca,

            categoria=
                categoria,

            ordem=ordem,
        )
    )

    (
        produtos,
        pagina,
        total_paginas,
        total_filtrado,
    ) = paginar_lista(
        produtos_filtrados,
        pagina,
    )

    return render_template(
        "link.html",

        pagina_ativa=
            "link",

        produtos=produtos,

        categorias=
            categorias,

        busca=busca,

        categoria_selecionada=
            categoria,

        ordem_selecionada=
            ordem,

        pagina=pagina,

        total_paginas=
            total_paginas,

        total_filtrado=
            total_filtrado,

        **metricas,
    )


# =========================================================
# PRONTOS
# =========================================================

@app.route(
    "/prontos"
)
@login_obrigatorio
def pagina_prontos():
    todos_produtos = (
        calcular_oportunidades(
            limite=None
        )
    )

    metricas = obter_metricas(
        todos_produtos
    )

    prontos = [
        produto
        for produto
        in todos_produtos

        if produto.get(
            "status"
        )
        == "pronto_publicar"
    ]

    prontos.sort(
        key=lambda produto:
            produto.get(
                "pontuacao",
                0
            ),
        reverse=True,
    )

    return render_template(
        "prontos.html",

        pagina_ativa=
            "prontos",

        produtos=prontos,

        **metricas,
    )


# =========================================================
# PUBLICADOS
# =========================================================

@app.route(
    "/publicados"
)
@login_obrigatorio
def pagina_publicados():
    metricas = (
        obter_metricas()
    )

    busca = (
        request.args.get(
            "busca",
            ""
        ).strip()
    )

    categoria = (
        request.args.get(
            "categoria",
            ""
        ).strip()
    )

    try:
        pagina = int(
            request.args.get(
                "pagina",
                1
            )
        )

    except ValueError:
        pagina = 1

    conexao = conectar()
    cursor = conexao.cursor()

    try:
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
                telegram_message_id,
                telegram_canal,
                telegram_chat_id,
                publicado_em

            FROM historico_publicacoes

            ORDER BY
                publicado_em DESC
            """
        )

        publicados = (
            cursor.fetchall()
        )

    finally:
        cursor.close()
        conexao.close()

    categorias = sorted(
        {
            item[
                "categoria"
            ]

            for item
            in publicados

            if item.get(
                "categoria"
            )
        }
    )

    if busca:
        termo = (
            busca.lower()
        )

        publicados = [
            item
            for item
            in publicados

            if termo
            in item.get(
                "nome",
                ""
            ).lower()
        ]

    if categoria:
        publicados = [
            item
            for item
            in publicados

            if item.get(
                "categoria"
            )
            == categoria
        ]

    (
        publicados_pagina,
        pagina,
        total_paginas,
        total_filtrado,
    ) = paginar_lista(
        publicados,
        pagina,
    )

    return render_template(
        "publicados.html",

        pagina_ativa=
            "publicados",

        publicados=
            publicados_pagina,

        categorias=
            categorias,

        busca=busca,

        categoria_selecionada=
            categoria,

        pagina=pagina,

        total_paginas=
            total_paginas,

        total_filtrado=
            total_filtrado,

        **metricas,
    )


# =========================================================
# INSTAGRAM
# =========================================================

@app.route(
    "/instagram"
)
@login_obrigatorio
def pagina_instagram():
    metricas = (
        obter_metricas()
    )

    resultado = (
        buscar_top_promocoes_do_dia(
            quantidade=5,
            max_por_categoria=2,
        )
    )

    artes = (
        listar_artes_do_dia()
    )

    return render_template(
        "instagram.html",

        pagina_ativa=
            "instagram",

        produtos=
            resultado["produtos"],

        total_publicados_hoje=
            resultado[
                "total_publicados_hoje"
            ],

        total_candidatos=
            resultado[
                "total_candidatos"
            ],

        data_referencia=
            resultado[
                "data_referencia"
            ],

        artes=artes,

        gerado=(
            request.args.get(
                "gerado"
            )
            == "1"
        ),

        erro_geracao=
            request.args.get(
                "erro",
                "",
            ),

        **metricas,
    )


@app.route(
    "/instagram/gerar",
    methods=["POST"],
)
@login_obrigatorio
def gerar_artes_instagram():
    resultado = (
        buscar_top_promocoes_do_dia(
            quantidade=5,
            max_por_categoria=2,
        )
    )

    produtos = (
        resultado[
            "produtos"
        ]
    )

    if not produtos:
        return redirect(
            url_for(
                "pagina_instagram",
                erro=(
                    "Nenhuma promoção válida "
                    "para gerar arte."
                ),
            )
        )

    try:
        gerar_artes_top(
            produtos
        )

    except Exception as erro:
        print(
            "Erro ao gerar artes "
            "do Instagram:"
        )

        print(
            erro
        )

        return redirect(
            url_for(
                "pagina_instagram",
                erro=str(
                    erro
                ),
            )
        )

    return redirect(
        url_for(
            "pagina_instagram",
            gerado=1,
        )
    )


# =========================================================
# CANAIS
# =========================================================

@app.route(
    "/canais"
)
@login_obrigatorio
def pagina_canais():
    metricas = (
        obter_metricas()
    )

    canais = (
        listar_canais(
            apenas_ativos=False
        )
    )

    return render_template(
        "canais.html",

        pagina_ativa=
            "canais",

        canais=canais,

        **metricas,
    )


# =========================================================
# SALVAR OFERTA
# =========================================================

@app.route(
    "/oportunidade/"
    "<int:oportunidade_id>/oferta",

    methods=["POST"],
)
@login_obrigatorio
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

    # Volta sempre para a página de preparação.
    # Se o formulário enviou os filtros atuais,
    # eles são preservados.
    return redirect(
        url_for(
            "pagina_link",
            busca=request.form.get(
                "retorno_busca",
                ""
            ),
            categoria=request.form.get(
                "retorno_categoria",
                ""
            ),
            ordem=request.form.get(
                "retorno_ordem",
                "score"
            ),
            pagina=request.form.get(
                "retorno_pagina",
                1
            ),
        )
    )


# =========================================================
# EXCLUIR OPORTUNIDADE
# =========================================================

@app.route(
    "/oportunidade/"
    "<int:oportunidade_id>/excluir",

    methods=["POST"],
)
@login_obrigatorio
def excluir_oportunidade_web(
    oportunidade_id
):
    excluir_oportunidade(
        oportunidade_id
    )

    return redirect(
        url_for(
            "pagina_link",

            busca=request.form.get(
                "retorno_busca",
                ""
            ),

            categoria=request.form.get(
                "retorno_categoria",
                ""
            ),

            ordem=request.form.get(
                "retorno_ordem",
                "score"
            ),

            pagina=request.form.get(
                "retorno_pagina",
                1
            ),
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
@login_obrigatorio
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
        request.referrer
        or url_for(
            "pagina_prontos"
        )
    )


# =========================================================
# CRON — PUBLICAÇÃO
# =========================================================

@app.route(
    "/tarefas/publicar",
    methods=["POST"],
)
@csrf.exempt
def tarefa_publicar():
    validar_cron()

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
        resultado = (
            publicar_proxima_promocao()
        )

        if resultado.get(
            "sucesso"
        ):
            return {
                "ok": True,
                "status": "publicado",

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
                "status": "fila_vazia",
                "mensagem":
                    "Nenhuma promoção pronta.",
            }

        return {
            "ok": False,
            "status": "erro",

            "erro":
                resultado.get(
                    "erro",
                    "Erro desconhecido."
                ),
        }

    except Exception as erro:
        return {
            "ok": False,
            "status": "erro",
            "erro": str(
                erro
            ),
        }, 500

    finally:
        _lock_publicacao.release()


# =========================================================
# CRON — COLETA
# =========================================================

def _executar_coleta_background():
    try:
        executar_coleta()

    except Exception as erro:
        print(
            "Erro na coleta automática:"
        )

        print(
            erro
        )

    finally:
        _lock_coleta.release()


@app.route(
    "/tarefas/coletar",
    methods=["POST"],
)
@csrf.exempt
def tarefa_coletar():
    validar_cron()

    if not _lock_coleta.acquire(
        blocking=False
    ):
        return {
            "ok": True,
            "status": "ocupado",
            "mensagem": (
                "Já existe uma coleta "
                "em andamento."
            ),
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
        "status": "iniciado",
        "mensagem": (
            "Coleta iniciada "
            "em segundo plano."
        ),
    }


# =========================================================
# HEALTH
# =========================================================

@app.route(
    "/health"
)
def health():
    return {
        "ok": True,
        "servico": "PromoConn",
    }


# =========================================================
# ERROS CSRF
# =========================================================

@app.errorhandler(
    CSRFError
)
def erro_csrf(
    erro
):
    if esta_logado():
        return (
            render_template(
                "erro.html",

                titulo=
                    "Sessão expirada",

                mensagem=(
                    "Atualize a página "
                    "e tente novamente."
                ),
            ),
            400,
        )

    return redirect(
        url_for(
            "login"
        )
    )


# =========================================================
# HEADERS DE SEGURANÇA
# =========================================================

@app.after_request
def headers_seguranca(
    resposta
):
    resposta.headers[
        "X-Content-Type-Options"
    ] = "nosniff"

    resposta.headers[
        "X-Frame-Options"
    ] = "DENY"

    resposta.headers[
        "Referrer-Policy"
    ] = "strict-origin-when-cross-origin"

    resposta.headers[
        "Permissions-Policy"
    ] = (
        "camera=(), "
        "microphone=(), "
        "geolocation=()"
    )

    return resposta


# =========================================================
# LOCAL
# =========================================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000,
    )
