from pathlib import Path
import base64
import mimetypes

import requests
from jinja2 import Template

from services.instagram.renderer import renderizar_html


BASE_DIR = Path(__file__).resolve().parents[2]

PASTA_SAIDA = (
    BASE_DIR
    / "static"
    / "img"
    / "instagram"
    / "geradas"
)

TEMPLATE_PATH = (
    BASE_DIR
    / "services"
    / "instagram"
    / "templates"
    / "oferta.html"
)

LOGO_PATH = (
    BASE_DIR
    / "static"
    / "img"
    / "instagram"
    / "logo.png"
)


def converter_numero(valor, padrao=0.0):
    """
    Converte valores que podem vir como:
        2498
        2498.50
        "2498.50"
        "2.498,50"
        "R$ 2.498,50"
        None

    para float.
    """

    if valor is None:
        return padrao

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()

    if not texto:
        return padrao

    # Remove moeda e espaços
    texto = (
        texto
        .replace("R$", "")
        .replace("r$", "")
        .replace(" ", "")
    )

    # Formato brasileiro: 2.498,50
    if "." in texto and "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    # Apenas vírgula: 2498,50
    elif "," in texto:
        texto = texto.replace(",", ".")

    try:
        return float(texto)

    except (ValueError, TypeError):
        return padrao


def preparar_imagem(origem):
    """
    Aceita:
    - URL http/https
    - caminho local
    - data URI

    Retorna uma imagem que o Playwright consiga renderizar.
    """

    if not origem:
        return ""

    origem = str(origem).strip()

    if origem.startswith("data:image/"):
        return origem

    # =========================================================
    # IMAGEM REMOTA
    # =========================================================

    if origem.startswith(("http://", "https://")):

        try:
            resposta = requests.get(
                origem,
                timeout=20,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 "
                        "Chrome/131.0 Safari/537.36"
                    )
                },
            )

            resposta.raise_for_status()

            content_type = resposta.headers.get(
                "Content-Type",
                "image/jpeg",
            )

            if not content_type.startswith("image/"):
                content_type = "image/jpeg"

            encoded = base64.b64encode(
                resposta.content
            ).decode("utf-8")

            print("✅ Imagem preparada para a arte.")

            return (
                f"data:{content_type};base64,{encoded}"
            )

        except Exception as erro:

            print(
                f"⚠️ Não foi possível baixar imagem: {erro}"
            )

            return origem

    # =========================================================
    # IMAGEM LOCAL
    # =========================================================

    caminho = Path(origem)

    if not caminho.is_absolute():
        caminho = BASE_DIR / caminho

    if not caminho.exists():

        print(
            f"⚠️ Imagem local não encontrada: {caminho}"
        )

        return ""

    try:

        mime = mimetypes.guess_type(
            str(caminho)
        )[0] or "image/png"

        encoded = base64.b64encode(
            caminho.read_bytes()
        ).decode("utf-8")

        return (
            f"data:{mime};base64,{encoded}"
        )

    except Exception as erro:

        print(
            f"⚠️ Erro ao preparar imagem local: {erro}"
        )

        return ""


def preparar_logo():
    """
    Carrega a logo ORIGINAL da PromoConn.

    O arquivo não é alterado nem recriado.
    """

    if not LOGO_PATH.exists():

        print(
            f"⚠️ Logo não encontrada: {LOGO_PATH}"
        )

        return ""

    try:

        mime = mimetypes.guess_type(
            str(LOGO_PATH)
        )[0] or "image/png"

        encoded = base64.b64encode(
            LOGO_PATH.read_bytes()
        ).decode("utf-8")

        print("✅ Logo original carregada.")

        return (
            f"data:{mime};base64,{encoded}"
        )

    except Exception as erro:

        print(
            f"⚠️ Erro ao carregar logo: {erro}"
        )

        return ""


def limpar_artes_anteriores():
    """
    Remove as artes anteriores para evitar
    que uma arte antiga apareça no lugar
    das artes novas.
    """

    PASTA_SAIDA.mkdir(
        parents=True,
        exist_ok=True,
    )

    removidas = 0

    for arquivo in PASTA_SAIDA.glob("*.png"):

        try:

            arquivo.unlink()
            removidas += 1

        except Exception as erro:

            print(
                f"⚠️ Não foi possível remover "
                f"{arquivo.name}: {erro}"
            )

    print(
        f"🧹 Artes antigas removidas: {removidas}"
    )


def carregar_template():

    if not TEMPLATE_PATH.exists():

        raise FileNotFoundError(
            f"Template não encontrado: {TEMPLATE_PATH}"
        )

    return Template(
        TEMPLATE_PATH.read_text(
            encoding="utf-8"
        )
    )


def gerar_arte(produto, caminho_saida):

    template = carregar_template()

    titulo = (
        produto.get("titulo")
        or produto.get("nome")
        or "Produto em oferta"
    )

    categoria = (
        produto.get("categoria")
        or ""
    )

    imagem_origem = (
        produto.get("imagem")
        or produto.get("imagem_url")
        or produto.get("thumbnail")
        or ""
    )

    # =========================================================
    # PREÇOS
    # =========================================================

    # Preço atual
    preco_atual = converter_numero(
        produto.get("preco_atual")
        or produto.get("preco"),
        0,
    )

    # Preço antigo
    #
    # IMPORTANTE:
    # Não usamos mais o preço atual como fallback.
    # Isso evita mostrar:
    #
    # ~~R$ 2.498,00~~
    # R$ 2.498,00
    #
    # quando o produto não possui desconto.
    preco_antigo = converter_numero(
        produto.get("preco_antigo")
        or produto.get("preco_original"),
        0,
    )

    # =========================================================
    # DESCONTO
    # =========================================================

    desconto = converter_numero(
        produto.get("desconto")
        or produto.get("desconto_instagram"),
        0,
    )

    # Só calcula desconto automaticamente quando
    # realmente existe um preço antigo maior que o atual.
    if (
        desconto <= 0
        and preco_antigo > preco_atual > 0
    ):

        desconto = (
            (preco_antigo - preco_atual)
            / preco_antigo
        ) * 100

    # Evita valores negativos
    if desconto < 0:
        desconto = 0

    # =========================================================
    # EXISTE DESCONTO REAL?
    # =========================================================

    tem_desconto = (
        preco_atual > 0
        and preco_antigo > preco_atual
        and desconto > 0
    )

    # Se não existe desconto real,
    # não enviamos preço antigo para o template.
    if not tem_desconto:

        preco_antigo = 0
        desconto = 0

    # =========================================================
    # RANKING
    # =========================================================

    ranking = produto.get("ranking") or 1

    try:

        ranking = int(ranking)

    except (ValueError, TypeError):

        ranking = 1

    # =========================================================
    # IMAGENS
    # =========================================================

    imagem = preparar_imagem(
        imagem_origem
    )

    logo = preparar_logo()

    # =========================================================
    # CONTEXTO DO TEMPLATE
    # =========================================================

    contexto = {
        "titulo": str(titulo),
        "categoria": str(categoria),
        "imagem": imagem,
        "logo": logo,
        "ranking": ranking,
        "preco_antigo": preco_antigo,
        "preco_atual": preco_atual,
        "desconto": desconto,
        "tem_desconto": tem_desconto,
    }

    html = template.render(
        **contexto
    )

    caminho_saida = Path(caminho_saida)

    renderizar_html(
        html,
        caminho_saida,
    )

    return caminho_saida


def gerar_artes_top(produtos):

    if not produtos:

        print(
            "⚠️ Nenhum produto recebido."
        )

        return []

    limpar_artes_anteriores()

    PASTA_SAIDA.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 60)
    print("📸 GERANDO ARTES REAIS DO INSTAGRAM")
    print("=" * 60)

    artes = []

    for posicao, produto in enumerate(
        produtos[:5],
        start=1,
    ):

        titulo = (
            produto.get("titulo")
            or produto.get("nome")
            or "Produto"
        )

        imagem = (
            produto.get("imagem")
            or produto.get("imagem_url")
            or produto.get("thumbnail")
            or ""
        )

        print()
        print(
            f"🛍️ Produto: {titulo}"
        )

        print(
            f"🖼️ Imagem: {imagem}"
        )

        produto_arte = dict(produto)

        produto_arte["ranking"] = posicao

        caminho_saida = (
            PASTA_SAIDA
            / f"top_{posicao}.png"
        )

        try:

            caminho = gerar_arte(
                produto_arte,
                caminho_saida,
            )

            print(
                f"✅ Arte {posicao} gerada: "
                f"{caminho}"
            )

            artes.append(
                caminho
            )

        except Exception as erro:

            print(
                f"❌ Erro ao gerar arte "
                f"{posicao}: {erro}"
            )

    print()
    print(
        f"📸 Total de artes geradas: "
        f"{len(artes)}"
    )

    print("=" * 60)

    return artes


def listar_artes_do_dia():

    if not PASTA_SAIDA.exists():
        return []

    arquivos = sorted(
        PASTA_SAIDA.glob("*.png"),
        key=lambda arquivo: arquivo.stat().st_mtime,
        reverse=True,
    )

    artes = []

    for arquivo in arquivos[:5]:

        nome = arquivo.stem

        try:

            posicao = int(
                nome.split("_")[-1]
            )

        except (ValueError, IndexError):

            posicao = 0

        artes.append(
            {
                "arquivo": (
                    "img/instagram/geradas/"
                    + arquivo.name
                ),
                "posicao": posicao,
            }
        )

    return artes