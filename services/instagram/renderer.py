from pathlib import Path

from playwright.sync_api import sync_playwright


LARGURA = 1080
ALTURA = 1350


# ============================================================
# CAMINHO DO PROJETO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]


def renderizar_html(
    html: str,
    caminho_saida: str | Path,
) -> Path:
    """
    Renderiza um HTML em PNG usando Chromium.

    O HTML é salvo temporariamente na raiz do projeto antes
    de ser aberto pelo Chromium.

    Isso permite que caminhos relativos, como:

        static/img/instagram/Post.png

    sejam encontrados corretamente.

    O resultado final é exatamente 1080x1350.
    """

    caminho_saida = Path(caminho_saida)

    caminho_saida.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # ARQUIVO HTML TEMPORÁRIO
    # ========================================================

    caminho_html_temp = BASE_DIR / "_oferta_render_temp.html"

    caminho_html_temp.write_text(
        html,
        encoding="utf-8",
    )

    try:

        with sync_playwright() as playwright:

            browser = playwright.chromium.launch(
                headless=True
            )

            page = browser.new_page(
                viewport={
                    "width": LARGURA,
                    "height": ALTURA,
                },
                device_scale_factor=1,
            )

            # =================================================
            # ABRE O HTML COMO ARQUIVO LOCAL
            # =================================================

            page.goto(
                caminho_html_temp.as_uri(),
                wait_until="networkidle",
            )

            # Aguarda imagens carregarem.
            page.wait_for_timeout(1000)

            # =================================================
            # TIRA O PRINT
            # =================================================

            page.screenshot(
                path=str(caminho_saida),
                full_page=False,
                type="png",
            )

            browser.close()

    finally:

        # Remove o HTML temporário.
        if caminho_html_temp.exists():
            caminho_html_temp.unlink()

    return caminho_saida