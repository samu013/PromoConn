import re
import unicodedata


class ClassificadorCategorias:
    """
    Decide o grupo usando path_from_root da categoria oficial.

    O título só é usado para desempatar Moda Masculina/Feminina
    quando a árvore oficial não informa claramente o gênero.
    """

    IDS_PRINCIPAIS = {
        "MLB1055": "Celulares",
        "MLB1144": "Games",
        "MLB1648": "Tecnologia",
        "MLB1574": "Casa",
        "MLB264201": "Esportes",
    }

    TERMOS_FEMININOS = {
        "feminino", "feminina", "mulher", "mulheres",
        "vestido", "vestidos", "saia", "saias",
        "sutia", "calcinha", "lingerie",
    }

    TERMOS_MASCULINOS = {
        "masculino", "masculina", "homem", "homens",
        "cueca", "cuecas", "gravata", "terno", "ternos",
    }

    def __init__(self, categorias):
        self.categorias = categorias

    @staticmethod
    def normalizar(texto):
        texto = str(texto or "").lower().strip()
        texto = unicodedata.normalize("NFKD", texto)

        texto = "".join(
            caractere
            for caractere in texto
            if not unicodedata.combining(caractere)
        )

        texto = re.sub(r"[^a-z0-9]+", " ", texto)

        return " ".join(texto.split())

    @staticmethod
    def _tem_termo(texto, termos):
        return bool(set(texto.split()).intersection(termos))

    def _classificar_moda(self, caminho_texto, titulo):
        oficial = self.normalizar(caminho_texto)
        titulo = self.normalizar(titulo)

        feminino_oficial = any(
            termo in oficial
            for termo in (
                "feminina", "feminino",
                "mulher", "mulheres",
            )
        )

        masculino_oficial = any(
            termo in oficial
            for termo in (
                "masculina", "masculino",
                "homem", "homens",
            )
        )

        if feminino_oficial and not masculino_oficial:
            return "Moda Feminina"

        if masculino_oficial and not feminino_oficial:
            return "Moda Masculina"

        feminino_titulo = self._tem_termo(
            titulo,
            self.TERMOS_FEMININOS,
        )

        masculino_titulo = self._tem_termo(
            titulo,
            self.TERMOS_MASCULINOS,
        )

        if feminino_titulo and not masculino_titulo:
            return "Moda Feminina"

        if masculino_titulo and not feminino_titulo:
            return "Moda Masculina"

        return None

    def classificar(self, categoria_id, titulo=None):
        caminho = self.categorias.caminho(categoria_id)

        if not caminho:
            return None

        ids = {
            str(item.get("id"))
            for item in caminho
            if item.get("id")
        }

        nomes = " | ".join(
            str(item.get("name") or "")
            for item in caminho
        )

        texto = self.normalizar(nomes)

        for categoria_raiz, grupo in self.IDS_PRINCIPAIS.items():
            if categoria_raiz in ids:
                return grupo

        indicadores_moda = any(
            termo in texto
            for termo in (
                "roupas",
                "calcados",
                "bolsas",
                "moda",
                "acessorios de moda",
            )
        )

        if indicadores_moda:
            return self._classificar_moda(
                nomes,
                titulo,
            )

        if any(
            termo in texto
            for termo in (
                "celulares",
                "smartphones",
                "telefonia",
            )
        ):
            return "Celulares"

        if any(
            termo in texto
            for termo in (
                "games",
                "video games",
                "consoles",
                "jogos para console",
            )
        ):
            return "Games"

        if any(
            termo in texto
            for termo in (
                "eletronicos",
                "informatica",
                "computadores",
                "audio",
                "cameras",
            )
        ):
            return "Tecnologia"

        if any(
            termo in texto
            for termo in (
                "casa",
                "moveis",
                "decoracao",
                "cozinha",
                "eletrodomesticos",
            )
        ):
            return "Casa"

        if any(
            termo in texto
            for termo in (
                "esportes",
                "fitness",
                "academia",
            )
        ):
            return "Esportes"

        return None
