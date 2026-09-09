from pathlib import Path
from playwright.sync_api import sync_playwright


LARGURA = 1080
ALTURA = 1350


def renderizar_html(
    html: str,
    caminho_saida: str | Path,
) -> Path:
    """
    Renderiza um HTML em PNG usando Chromium.

    O resultado final é exatamente 1080x1350,
    formato ideal para publicação no feed do Instagram.
    """

    caminho_saida = Path(caminho_saida)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)

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

        page.set_content(
            html,
            wait_until="networkidle",
        )

        # Aguarda imagens carregarem.
        page.wait_for_timeout(1000)

        page.screenshot(
            path=str(caminho_saida),
            full_page=False,
            type="png",
        )

        browser.close()

    return caminho_saida