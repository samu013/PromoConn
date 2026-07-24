from mercadolivre.browser import Browser


class Coletor:

    def __init__(self):
        self.browser = Browser()

    def buscar(self, palavra):
        page = self.browser.page

        print("Abrindo Mercado Livre...")

        self.browser.abrir(
            "https://www.mercadolivre.com.br"
        )

        self.browser.esperar(3000)

        print("Página inicial:")
        print(page.url)

        campo_busca = page.locator(
            'input[name="as_word"]'
        ).first

        try:
            campo_busca.wait_for(
                state="visible",
                timeout=10000
            )
        except Exception:
            print("❌ Campo de pesquisa não encontrado.")
            return []

        print(f'Pesquisando: "{palavra}"')

        campo_busca.click()
        campo_busca.fill(palavra)

        self.browser.esperar(700)

        campo_busca.press("Enter")

        try:
            page.wait_for_load_state(
                "domcontentloaded",
                timeout=15000
            )
        except Exception:
            pass

        self.browser.esperar(5000)

        print("URL depois da pesquisa:")
        print(page.url)

        # Detecta se o ML pediu nova verificação
        url_atual = page.url.lower()

        if (
            "account-verification" in url_atual
            or "/login" in url_atual
        ):
            print("⚠️ Mercado Livre pediu verificação/login.")
            return []

        # Tenta encontrar os cards da busca
        cards = page.locator(".ui-search-result")

        quantidade = cards.count()

        print(f"Produtos encontrados: {quantidade}")

        produtos = []

        for i in range(quantidade):
            card = cards.nth(i)

            try:
                titulo = card.locator(
                    ".poly-component__title"
                ).first.inner_text()
            except Exception:
                titulo = ""

            try:
                preco = card.locator(
                    ".andes-money-amount__fraction"
                ).first.inner_text()
            except Exception:
                preco = ""

            try:
                link = card.locator(
                    "a"
                ).first.get_attribute("href")
            except Exception:
                link = ""

            if titulo:
                produtos.append({
                    "titulo": titulo.strip(),
                    "preco": preco.strip(),
                    "link": link
                })

        return produtos

    def fechar(self):
        self.browser.fechar()   