import io
import math
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps


FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")

LARGURA = 1080
ALTURA = 1350

AZUL = "#071B55"
AZUL_CLARO = "#168FD2"
VERDE = "#75C82D"
VERDE_CLARO = "#9BE95C"
AMARELO = "#FFB400"
BRANCO = "#FFFFFF"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_ROOT = PROJECT_ROOT / "static"
TEMPLATE_PATH = STATIC_ROOT / "img" / "instagram" / "modelo_base_limpo.png"
GERADAS_ROOT = STATIC_ROOT / "instagram" / "geradas"


# =========================================================
# FONTES
# =========================================================

def _fonte(tamanho, bold=False, condensed=False):
    candidatos = []

    if condensed and bold:
        candidatos += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSansNarrow-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]

    elif bold:
        candidatos += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]

    else:
        candidatos += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]

    for caminho in candidatos:
        if Path(caminho).exists():
            return ImageFont.truetype(caminho, tamanho)

    return ImageFont.load_default()


# =========================================================
# UTILITÁRIOS
# =========================================================

def _moeda(valor):
    valor = float(valor)

    texto = (
        f"{valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"R${texto}"


def _largura_texto(draw, texto, fonte):
    bbox = draw.textbbox((0, 0), texto, font=fonte)
    return bbox[2] - bbox[0]


def _quebrar_texto(draw, texto, fonte, largura_maxima, max_linhas=3):
    palavras = str(texto or "").upper().split()
    linhas = []
    atual = ""

    for palavra in palavras:
        teste = f"{atual} {palavra}".strip()

        if _largura_texto(draw, teste, fonte) <= largura_maxima:
            atual = teste
            continue

        if atual:
            linhas.append(atual)

        atual = palavra

        if len(linhas) >= max_linhas - 1:
            break

    if atual and len(linhas) < max_linhas:
        linhas.append(atual)

    return linhas[:max_linhas]


def _titulo_ajustado(draw, titulo):
    """
    Título limitado à área original do modelo.
    Nunca deixa texto escapar para dentro do círculo.
    """
    for tamanho in range(46, 27, -2):
        fonte = _fonte(tamanho, bold=True, condensed=True)
        linhas = _quebrar_texto(
            draw,
            titulo,
            fonte,
            largura_maxima=570,
            max_linhas=3,
        )

        if len(linhas) <= 3:
            altura = len(linhas) * (tamanho + 8)
            if altura <= 145:
                return fonte, linhas, tamanho

    fonte = _fonte(28, bold=True, condensed=True)
    return fonte, _quebrar_texto(draw, titulo, fonte, 570, 3), 28


def _baixar_imagem(url):
    resposta = requests.get(
        url,
        timeout=25,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    resposta.raise_for_status()

    return Image.open(io.BytesIO(resposta.content)).convert("RGBA")


# =========================================================
# PRODUTO COM RECORTE NO CÍRCULO
# =========================================================

def _colar_produto_no_circulo(imagem, url):
    produto = _baixar_imagem(url)

    # Mantém produto sempre menor que a área útil do círculo.
    produto = ImageOps.contain(produto, (300, 300))

    # Canvas transparente exatamente no tamanho da área interna.
    area_w = 350
    area_h = 350
    area = Image.new("RGBA", (area_w, area_h), (255, 255, 255, 0))

    px = (area_w - produto.width) // 2
    py = (area_h - produto.height) // 2
    area.alpha_composite(produto, (px, py))

    # Máscara circular/oval para impedir QUALQUER pixel de escapar.
    mask = Image.new("L", (area_w, area_h), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((0, 0, area_w - 1, area_h - 1), fill=255)

    # Fundo branco dentro da área mascarada.
    fundo = Image.new("RGBA", (area_w, area_h), (255, 255, 255, 255))
    fundo.alpha_composite(area)

    # Posição central dentro do aro do template.
    destino_x = 712
    destino_y = 350

    imagem.paste(
        fundo,
        (destino_x, destino_y),
        mask,
    )


# =========================================================
# SELO DE DESCONTO
# =========================================================

def _selo_pontos(cx, cy, re, ri, pontas=18):
    pontos = []

    for i in range(pontas * 2):
        ang = -math.pi / 2 + i * math.pi / pontas
        r = re if i % 2 == 0 else ri
        pontos.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))

    return pontos


def _desenhar_selo(draw, desconto):
    if desconto <= 0:
        return

    # Abaixo dos benefícios, sem encostar no texto.
    cx = 405
    cy = 725

    draw.polygon(
        _selo_pontos(cx, cy, 72, 62),
        fill="#B8EF79",
        outline="#70C82D",
    )

    draw.text(
        (cx, cy),
        f"{desconto:.0f}% OFF",
        anchor="mm",
        font=_fonte(24, bold=True, condensed=True),
        fill=BRANCO,
        stroke_width=1,
        stroke_fill="#70C82D",
    )


# =========================================================
# PREÇOS
# =========================================================

def _fonte_que_cabe(draw, texto, tamanho_inicial, tamanho_minimo, largura):
    for tamanho in range(tamanho_inicial, tamanho_minimo - 1, -2):
        fonte = _fonte(tamanho, bold=True, condensed=True)
        if _largura_texto(draw, texto, fonte) <= largura:
            return fonte

    return _fonte(tamanho_minimo, bold=True, condensed=True)


def _desenhar_precos(draw, produto):
    preco = float(produto["preco"])
    anterior = produto.get("preco_original")

    # Bloco totalmente separado em três níveis:
    # DE / preço antigo
    # POR
    # preço atual
    if anterior is not None and float(anterior) > preco:
        texto_antigo = _moeda(anterior)

        draw.text(
            (260, 805),
            "DE",
            font=_fonte(25, bold=True, condensed=True),
            fill=AZUL_CLARO,
        )

        fonte_antigo = _fonte_que_cabe(
            draw,
            texto_antigo,
            tamanho_inicial=37,
            tamanho_minimo=27,
            largura=250,
        )

        draw.text(
            (260, 838),
            texto_antigo,
            font=fonte_antigo,
            fill=AZUL_CLARO,
        )

        bbox = draw.textbbox(
            (260, 838),
            texto_antigo,
            font=fonte_antigo,
        )

        y_risco = (bbox[1] + bbox[3]) // 2

        draw.line(
            (bbox[0] - 2, y_risco, bbox[2] + 2, y_risco),
            fill=AZUL_CLARO,
            width=4,
        )

    draw.text(
        (475, 855),
        "POR",
        font=_fonte(29, bold=True, condensed=True),
        fill=AMARELO,
    )

    texto_atual = _moeda(preco)

    fonte_atual = _fonte_que_cabe(
        draw,
        texto_atual,
        tamanho_inicial=54,
        tamanho_minimo=38,
        largura=305,
    )

    draw.text(
        (305, 918),
        texto_atual,
        font=fonte_atual,
        fill=AMARELO,
        stroke_width=1,
        stroke_fill=AMARELO,
    )


# =========================================================
# ARTE
# =========================================================

def gerar_arte_produto(produto, destino, posicao):
    if not TEMPLATE_PATH.exists():
        raise RuntimeError(
            f"Template limpo não encontrado: {TEMPLATE_PATH}"
        )

    imagem = Image.open(TEMPLATE_PATH).convert("RGB")
    draw = ImageDraw.Draw(imagem)

    # -----------------------------------------------------
    # TÍTULO
    # -----------------------------------------------------
    fonte_titulo, linhas, tamanho = _titulo_ajustado(
        draw,
        produto.get("nome", "Produto"),
    )

    y = 345

    for linha in linhas:
        draw.text(
            (52, y),
            linha,
            font=fonte_titulo,
            fill=AZUL,
        )
        y += tamanho + 8

    # -----------------------------------------------------
    # INFORMAÇÕES
    # -----------------------------------------------------
    categoria = produto.get("categoria") or "Geral"
    ranking = produto.get("ranking")

    infos = [
        "Uma das melhores promoções do dia",
        f"Categoria: {categoria}",
        (
            f"Ranking Mercado Livre: #{ranking}"
            if ranking is not None
            else "Confira a oferta no nosso grupo"
        ),
    ]

    y_info = max(505, y + 25)

    for info in infos:
        # Evita chegar perto do selo.
        if y_info > 625:
            break

        draw.text(
            (52, y_info),
            "✓",
            font=_fonte(29, bold=True),
            fill="#00B61F",
        )

        # Reduz a fonte até cada info caber em uma única linha.
        fonte_info = _fonte_que_cabe(
            draw,
            info,
            tamanho_inicial=27,
            tamanho_minimo=20,
            largura=515,
        )

        draw.text(
            (88, y_info + 1),
            info,
            font=fonte_info,
            fill=AZUL,
        )

        y_info += 50

    # -----------------------------------------------------
    # PRODUTO
    # -----------------------------------------------------
    _colar_produto_no_circulo(
        imagem,
        produto["imagem"],
    )

    # -----------------------------------------------------
    # DESCONTO E PREÇOS
    # -----------------------------------------------------
    desconto = float(
        produto.get("desconto_instagram", 0) or 0
    )

    _desenhar_selo(draw, desconto)
    _desenhar_precos(draw, produto)

    # -----------------------------------------------------
    # SALVAR
    # -----------------------------------------------------
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

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

def _normalizar_nome_arquivo(texto):
    texto = str(texto or "produto")
    texto = re.sub(r"[^a-zA-Z0-9_-]+", "_", texto)
    texto = re.sub(r"_+", "_", texto)
    return texto.strip("_")[:60] or "produto"


def gerar_artes_top(produtos):
    data = datetime.now(FUSO_BRASIL).strftime("%Y-%m-%d")
    pasta = GERADAS_ROOT / data
    pasta.mkdir(parents=True, exist_ok=True)

    # Recria as artes do dia.
    for antigo in pasta.glob("*.jpg"):
        antigo.unlink(missing_ok=True)

    artes = []

    for posicao, produto in enumerate(produtos, start=1):
        ml_id = _normalizar_nome_arquivo(produto.get("ml_id"))
        arquivo = pasta / f"{posicao:02d}_{ml_id}.jpg"

        gerar_arte_produto(
            produto=produto,
            destino=arquivo,
            posicao=posicao,
        )

        artes.append({
            "posicao": posicao,
            "nome": produto.get("nome"),
            "ml_id": produto.get("ml_id"),
            "arquivo": arquivo.relative_to(STATIC_ROOT).as_posix(),
        })

    return {
        "data_chave": data,
        "artes": artes,
    }


def listar_artes_do_dia():
    data = datetime.now(FUSO_BRASIL).strftime("%Y-%m-%d")
    pasta = GERADAS_ROOT / data

    if not pasta.exists():
        return []

    artes = []

    for arquivo in sorted(pasta.glob("*.jpg")):
        try:
            posicao = int(arquivo.stem.split("_", 1)[0])
        except (ValueError, IndexError):
            posicao = 999

        artes.append({
            "posicao": posicao,
            "arquivo": arquivo.relative_to(STATIC_ROOT).as_posix(),
        })

    return artes
