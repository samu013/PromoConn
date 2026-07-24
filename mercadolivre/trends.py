from config import TERMOS_BLOQUEADOS
from mercadolivre.client import MercadoLivreClient


class Trends:

    def __init__(self):
        self.client = MercadoLivreClient()

    def buscar(self):
        resposta = self.client.get("/trends/MLB")

        if resposta.status_code != 200:
            print(
                f"❌ Erro ao buscar tendências: "
                f"{resposta.status_code}"
            )
            print(resposta.text)
            return []

        tendencias = []

        for posicao, item in enumerate(
            resposta.json(),
            start=1
        ):
            palavra = item.get("keyword", "").strip()
            url = item.get("url")

            if not palavra:
                continue

            if self._bloqueado(palavra):
                print(
                    f"🚫 Ignorado: {palavra}"
                )
                continue

            tendencias.append({
                "palavra": palavra,
                "url": url,
                "posicao": posicao,
            })

        return tendencias

    def _bloqueado(self, palavra):
        texto = palavra.lower()

        return any(
            termo.lower() in texto
            for termo in TERMOS_BLOQUEADOS
        )