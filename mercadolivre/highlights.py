from mercadolivre.client import MercadoLivreClient


class Highlights:

    def __init__(self):
        self.client = MercadoLivreClient()

    def buscar(self, categoria_id):
        endpoint = (
            f"/highlights/MLB/category/{categoria_id}"
        )

        resposta = self.client.get(endpoint)

        if resposta.status_code != 200:
            print(
                f"❌ Erro ao buscar highlights: "
                f"{resposta.status_code}"
            )
            print(resposta.text)
            return []

        resultados = resposta.json().get("content", [])

        produtos = []

        for resultado in resultados:

            produto_id = resultado.get("id")
            tipo = resultado.get("type")
            posicao = resultado.get("position")

            detalhe = self._buscar_detalhe(
                produto_id,
                tipo
            )

            if not detalhe:
                continue

            produtos.append({
                "id": produto_id,
                "tipo": tipo,
                "ranking": posicao,
                "nome": detalhe.get("nome"),
                "imagem": detalhe.get("imagem"),
                "user_id": detalhe.get("user_id"),
            })

        return produtos

    def _buscar_detalhe(self, produto_id, tipo):

        if tipo == "PRODUCT":

            resposta = self.client.get(
                f"/products/{produto_id}"
            )

            if resposta.status_code != 200:
                return None

            dados = resposta.json()

            imagens = dados.get("pictures", [])

            imagem = None

            if imagens:
                imagem = imagens[0].get("url")

            return {
                "nome": dados.get("name"),
                "imagem": imagem,
                "user_id": None,
            }

        if tipo == "USER_PRODUCT":

            resposta = self.client.get(
                f"/user-products/{produto_id}"
            )

            if resposta.status_code != 200:
                return None

            dados = resposta.json()

            thumbnail = dados.get("thumbnail") or {}

            return {
                "nome": dados.get("name"),
                "imagem": thumbnail.get("secure_url"),
                "user_id": dados.get("user_id"),
            }

        return None