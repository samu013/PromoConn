import subprocess
import time

from playwright.sync_api import sync_playwright


CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE_PATH = r"C:\ChromeBot"
DEBUG_PORT = 9222


class Browser:
    def __init__(self):
        self.chrome_process = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        self._iniciar_chrome()
        self._conectar_playwright()

    def _iniciar_chrome(self):
        print("Abrindo Google Chrome...")

        self.chrome_process = subprocess.Popen(
            [
                CHROME_PATH,
                f"--remote-debugging-port={DEBUG_PORT}",
                f"--user-data-dir={PROFILE_PATH}",
                "--start-maximized",
            ]
        )

        # Dá tempo para o Chrome iniciar
        time.sleep(3)

    def _conectar_playwright(self):
        print("Conectando Playwright ao Chrome...")

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.connect_over_cdp(
            f"http://127.0.0.1:{DEBUG_PORT}"
        )

        if not self.browser.contexts:
            raise RuntimeError(
                "Nenhum contexto do Chrome foi encontrado."
            )

        self.context = self.browser.contexts[0]

        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()

        print("✅ Chrome conectado.")

    def abrir(self, url):
        print(f"Abrindo: {url}")

        self.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

    def esperar(self, ms):
        self.page.wait_for_timeout(ms)

    def fechar(self):
        # Fechamos apenas a conexão do Playwright.
        # Não é necessário matar o Chrome à força.
        if self.playwright:
            self.playwright.stop()