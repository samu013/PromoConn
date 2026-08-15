import io
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageOps,
)


FUSO_BRASIL = ZoneInfo(
    "America/Sao_Paulo"
)

LARGURA = 1080
ALTURA = 1350

AZUL = "#00154D"
AZUL_TEXTO = "#03164D"
AZUL_PRECO = "#128FD5"
VERDE = "#79C92C"
VERDE_CLARO = "#9BE95C"
AMARELO = "#FFB900"
BRANCO = "#FFFFFF"
PRETO = "#111111"

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
)

STATIC_ROOT = (
    PROJECT_ROOT
    / "static"
)

TEMPLATE_PATH = (
    STATIC_ROOT
    / "img"
    / "instagram"
    / "modelo_base.png"
)

GERADAS_ROOT = (
    STATIC_ROOT
    / "instagram"
    / "geradas"
)


# =========================================================
# FONTES
# =========================================================

def _fonte(
    tamanho,
    bold=False,
    condensed=False,
):
    candidatos = []

    if condensed and bold:
        candidatos.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
            "/usr/share/fonts/truetype/paratype/PTN77F.ttf",
        ])

    if bold:
        candidatos.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf",
            "C:/Windows/Fonts/arialbd.ttf",
        ])

    else:
        candidatos.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
            "C:/Windows/Fonts/arial.ttf",
        ])

    for caminho in candidatos:
        if Path(caminho).exists():
            return ImageFont.truetype(
                caminho,
                tamanho,
            )

    return ImageFont.load_default()


# =========================================================
# TEXTO
# =========================================================

def _moeda(
    valor
):
    valor = float(
        valor
    )

    texto = (
        f"{valor:,.2f}"
        .replace(
            ",",
            "X",
        )
        .replace(
            ".",
            ",",
        )
        .replace(
            "X",
            ".",
        )
    )

    return f"R${texto}"


def _quebrar_texto(
    draw,
    texto,
    font,
    largura_maxima,
    max_linhas,
):
    palavras = (
        str(
            texto
            or ""
        )
        .upper()
        .split()
    )

    linhas = []
    atual = ""

    for palavra in palavras:
        teste = (
            f"{atual} {palavra}"
            .strip()
        )

        bbox = draw.textbbox(
            (0, 0),
            teste,
            font=font,
        )

        largura = (
            bbox[2]
            - bbox[0]
        )

        if largura <= largura_maxima:
            atual = teste
            continue

        if atual:
            linhas.append(
                atual
            )

        atual = palavra

        if len(linhas) >= max_linhas - 1:
            break

    if atual and len(linhas) < max_linhas:
        linhas.append(
            atual
        )

    return linhas[:max_linhas]


def _reduzir_titulo(
    draw,
    texto,
):
    """
    O modelo original usa um título grande em no máximo
    duas linhas. Reduzimos a fonte até caber na mesma área.
    """

    for tamanho in range(
        48,
        31,
        -2,
    ):
        fonte = _fonte(
            tamanho,
            bold=True,
            condensed=True,
        )

        linhas = _quebrar_texto(
            draw,
            texto,
            fonte,
            largura_maxima=590,
            max_linhas=2,
        )

        if len(linhas) <= 2:
            altura = len(linhas) * (
                tamanho + 7
            )

            if altura <= 112:
                return (
                    fonte,
                    linhas,
                    tamanho,
                )

    fonte = _fonte(
        30,
        bold=True,
        condensed=True,
    )

    linhas = _quebrar_texto(
        draw,
        texto,
        fonte,
        largura_maxima=590,
        max_linhas=2,
    )

    return (
        fonte,
        linhas,
        30,
    )


# =========================================================
# TEMPLATE ORIGINAL
# =========================================================

def _carregar_template():
    if not TEMPLATE_PATH.exists():
        raise RuntimeError(
            "Template do Instagram não encontrado: "
            f"{TEMPLATE_PATH}"
        )

    imagem = Image.open(
        TEMPLATE_PATH
    ).convert(
        "RGB"
    )

    if imagem.size != (
        LARGURA,
        ALTURA,
    ):
        imagem = imagem.resize(
            (
                LARGURA,
                ALTURA,
            )
        )

    draw = ImageDraw.Draw(
        imagem
    )

    # -----------------------------------------------------
    # APAGA SOMENTE OS ELEMENTOS VARIÁVEIS DO POST ORIGINAL
    # -----------------------------------------------------
    #
    # Todo o resto permanece PIXEL A PIXEL igual ao modelo:
    # fundo, logo, molduras, circuitos, mascotes e rodapé.

    # Título + benefícios.
    draw.rectangle(
        (
            45,
            335,
            635,
            650,
        ),
        fill=BRANCO,
    )

    # Selo de desconto original.
    draw.rectangle(
        (
            292,
            650,
            525,
            800,
        ),
        fill=BRANCO,
    )

    # Preços originais.
    draw.rectangle(
        (
            245,
            795,
            570,
            1000,
        ),
        fill=BRANCO,
    )

    # Limpa o interior do círculo do produto,
    # preservando as bordas dourada/preta originais.
    draw.ellipse(
        (
            706,
            331,
            1068,
            724,
        ),
        fill=BRANCO,
    )

    return imagem


# =========================================================
# PRODUTO
# =========================================================

def _baixar_imagem_produto(
    url
):
    resposta = requests.get(
        url,
        timeout=25,
        headers={
            "User-Agent":
                "Mozilla/5.0"
        },
    )

    resposta.raise_for_status()

    return Image.open(
        io.BytesIO(
            resposta.content
        )
    ).convert(
        "RGBA"
    )


def _desenhar_produto(
    imagem,
    url_imagem,
):
    produto = (
        _baixar_imagem_produto(
            url_imagem
        )
    )

    # Mantém margens internas como no modelo original.
    produto = ImageOps.contain(
        produto,
        (
            315,
            315,
        ),
    )

    x = (
        887
        - produto.width // 2
    )

    y = (
        528
        - produto.height // 2
    )

    imagem.paste(
        produto,
        (
            x,
            y,
        ),
        produto,
    )


# =========================================================
# SELO
# =========================================================

def _pontos_selo(
    cx,
    cy,
    raio_externo,
    raio_interno,
    pontas=18,
):
    import math

    pontos = []

    for indice in range(
        pontas * 2
    ):
        angulo = (
            -math.pi / 2
            + indice
            * math.pi
            / pontas
        )

        raio = (
            raio_externo
            if indice % 2 == 0
            else raio_interno
        )

        pontos.append(
            (
                cx
                + math.cos(
                    angulo
                )
                * raio,

                cy
                + math.sin(
                    angulo
                )
                * raio,
            )
        )

    return pontos


def _desenhar_selo(
    draw,
    desconto,
):
    if desconto <= 0:
        return

    cx = 405
    cy = 720

    pontos = _pontos_selo(
        cx,
        cy,
        79,
        70,
    )

    draw.polygon(
        pontos,
        fill="#B7F078",
        outline="#70C82E",
    )

    # Pequenos traços ao redor, como no modelo.
    for inicio, fim in [
        ((405, 625), (405, 642)),
        ((355, 635), (365, 650)),
        ((455, 635), (445, 650)),
        ((320, 678), (338, 683)),
        ((490, 678), (472, 683)),
        ((318, 746), (337, 742)),
        ((492, 746), (473, 742)),
        ((350, 795), (360, 779)),
        ((460, 795), (450, 779)),
    ]:
        draw.line(
            (
                inicio,
                fim,
            ),
            fill="#70C82E",
            width=3,
        )

    texto = (
        f"{desconto:.0f}% OFF"
    )

    draw.text(
        (
            cx,
            cy,
        ),
        texto,
        anchor="mm",
        font=_fonte(
            24,
            bold=True,
            condensed=True,
        ),
        fill=BRANCO,
        stroke_width=1,
        stroke_fill="#70C82E",
    )


# =========================================================
# ARTE
# =========================================================

def gerar_arte_produto(
    produto,
    destino,
    posicao,
):
    imagem = (
        _carregar_template()
    )

    draw = ImageDraw.Draw(
        imagem
    )

    # -----------------------------------------------------
    # TÍTULO — MESMA ÁREA DO MODELO
    # -----------------------------------------------------

    fonte_titulo, linhas, tamanho = (
        _reduzir_titulo(
            draw,
            produto.get(
                "nome"
            ),
        )
    )

    y = 345

    for linha in linhas:
        draw.text(
            (
                52,
                y,
            ),
            linha,
            font=fonte_titulo,
            fill=AZUL_TEXTO,
            stroke_width=1,
            stroke_fill=AZUL_TEXTO,
        )

        y += (
            tamanho
            + 10
        )

    # -----------------------------------------------------
    # 3 LINHAS — MESMA POSIÇÃO DO MODELO
    # -----------------------------------------------------
    #
    # Não inventamos benefícios técnicos. Mantemos o mesmo
    # visual usando dados reais que o PromoConn já possui.

    categoria = (
        produto.get(
            "categoria"
        )
        or "Geral"
    )

    ranking = (
        produto.get(
            "ranking"
        )
    )

    linha_1 = "Uma das melhores promoções do dia"
    linha_2 = f"Categoria: {categoria}"

    if ranking is not None:
        linha_3 = (
            f"Ranking Mercado Livre: #{ranking}"
        )
    else:
        linha_3 = (
            "Confira a oferta no nosso grupo"
        )

    bullets = [
        linha_1,
        linha_2,
        linha_3,
    ]

    fonte_bullet = _fonte(
        27,
        bold=False,
        condensed=True,
    )

    fonte_check = _fonte(
        31,
        bold=True,
    )

    bullet_y = 500

    for texto in bullets:
        draw.text(
            (
                51,
                bullet_y,
            ),
            "✓",
            font=fonte_check,
            fill="#00B915",
        )

        # Mantém cada linha em UMA linha sempre que possível.
        tamanho_bullet = 27
        fonte_atual = fonte_bullet

        while tamanho_bullet > 20:
            bbox = draw.textbbox(
                (
                    0,
                    0,
                ),
                texto,
                font=fonte_atual,
            )

            if (
                bbox[2]
                - bbox[0]
                <= 520
            ):
                break

            tamanho_bullet -= 1

            fonte_atual = _fonte(
                tamanho_bullet,
                bold=False,
                condensed=True,
            )

        draw.text(
            (
                88,
                bullet_y + 2,
            ),
            texto,
            font=fonte_atual,
            fill=AZUL_TEXTO,
        )

        bullet_y += 52

    # -----------------------------------------------------
    # PRODUTO — DENTRO DO MESMO CÍRCULO DO MODELO
    # -----------------------------------------------------

    _desenhar_produto(
        imagem,
        produto[
            "imagem"
        ],
    )

    # -----------------------------------------------------
    # DESCONTO
    # -----------------------------------------------------

    desconto = float(
        produto.get(
            "desconto_instagram",
            0,
        )
        or 0
    )

    _desenhar_selo(
        draw,
        desconto,
    )

    # -----------------------------------------------------
    # PREÇOS — MESMA HIERARQUIA / POSIÇÃO DO MODELO
    # -----------------------------------------------------

    preco = float(
        produto[
            "preco"
        ]
    )

    preco_original = (
        produto.get(
            "preco_original"
        )
    )

    if (
        preco_original is not None
        and float(
            preco_original
        ) > preco
    ):
        draw.text(
            (
                262,
                805,
            ),
            "DE",
            font=_fonte(
                27,
                bold=True,
                condensed=True,
            ),
            fill=AZUL_PRECO,
        )

        texto_antigo = _moeda(
            preco_original
        )

        fonte_antigo = _fonte(
            39,
            bold=True,
            condensed=True,
        )

        draw.text(
            (
                262,
                838,
            ),
            texto_antigo,
            font=fonte_antigo,
            fill=AZUL_PRECO,
        )

        bbox = draw.textbbox(
            (
                262,
                838,
            ),
            texto_antigo,
            font=fonte_antigo,
        )

        meio = (
            bbox[1]
            + bbox[3]
        ) // 2

        draw.line(
            (
                bbox[0] - 3,
                meio,
                bbox[2] + 3,
                meio,
            ),
            fill=AZUL_PRECO,
            width=4,
        )

    draw.text(
        (
            474,
            850,
        ),
        "POR",
        font=_fonte(
            34,
            bold=True,
            condensed=True,
        ),
        fill=AMARELO,
    )

    # Preço atual com ajuste automático para não invadir o mascote.
    texto_preco = _moeda(
        preco
    )

    tamanho_preco = 58

    while tamanho_preco >= 42:
        fonte_preco = _fonte(
            tamanho_preco,
            bold=True,
            condensed=True,
        )

        bbox = draw.textbbox(
            (
                0,
                0,
            ),
            texto_preco,
            font=fonte_preco,
        )

        if (
            bbox[2]
            - bbox[0]
            <= 295
        ):
            break

        tamanho_preco -= 2

    draw.text(
        (
            304,
            908,
        ),
        texto_preco,
        font=fonte_preco,
        fill=AMARELO,
        stroke_width=1,
        stroke_fill=AMARELO,
    )

    # -----------------------------------------------------
    # SALVA
    # -----------------------------------------------------

    destino = Path(
        destino
    )

    destino.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    imagem.save(
        destino,
        "JPEG",
        quality=95,
        optimize=True,
    )

    return destino


# =========================================================
# LOTE
# =========================================================

def _normalizar_nome_arquivo(
    texto
):
    texto = str(
        texto
        or "produto"
    )

    texto = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        texto,
    )

    texto = re.sub(
        r"_+",
        "_",
        texto,
    )

    return (
        texto.strip(
            "_"
        )[:60]
        or "produto"
    )


def gerar_artes_top(
    produtos
):
    agora = datetime.now(
        FUSO_BRASIL
    )

    chave_data = (
        agora.strftime(
            "%Y-%m-%d"
        )
    )

    pasta = (
        GERADAS_ROOT
        / chave_data
    )

    pasta.mkdir(
        parents=True,
        exist_ok=True,
    )

    for antigo in pasta.glob(
        "*.jpg"
    ):
        antigo.unlink(
            missing_ok=True
        )

    artes = []

    for posicao, produto in enumerate(
        produtos,
        start=1,
    ):
        ml_id = _normalizar_nome_arquivo(
            produto.get(
                "ml_id"
            )
        )

        nome_arquivo = (
            f"{posicao:02d}_{ml_id}.jpg"
        )

        caminho = (
            pasta
            / nome_arquivo
        )

        gerar_arte_produto(
            produto=produto,
            destino=caminho,
            posicao=posicao,
        )

        relativo_static = (
            caminho.relative_to(
                STATIC_ROOT
            )
            .as_posix()
        )

        artes.append({
            "posicao":
                posicao,

            "nome":
                produto.get(
                    "nome"
                ),

            "ml_id":
                produto.get(
                    "ml_id"
                ),

            "arquivo":
                relativo_static,
        })

    return {
        "data_chave":
            chave_data,

        "artes":
            artes,
    }


def listar_artes_do_dia():
    chave_data = (
        datetime.now(
            FUSO_BRASIL
        )
        .strftime(
            "%Y-%m-%d"
        )
    )

    pasta = (
        GERADAS_ROOT
        / chave_data
    )

    if not pasta.exists():
        return []

    artes = []

    for caminho in sorted(
        pasta.glob(
            "*.jpg"
        )
    ):
        nome = caminho.stem

        try:
            posicao = int(
                nome.split(
                    "_",
                    1,
                )[0]
            )

        except (
            ValueError,
            IndexError,
        ):
            posicao = 999

        artes.append({
            "posicao":
                posicao,

            "arquivo":
                caminho.relative_to(
                    STATIC_ROOT
                ).as_posix(),
        })

    return artes
