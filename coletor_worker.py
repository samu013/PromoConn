import threading
import time

from database.database import criar_tabelas
from database.oportunidades import salvar_oportunidade
from database.tendencias import desativar_todas, salvar_tendencia
from mercadolivre.categorias import CategoriasMercadoLivre
from mercadolivre.classificador import ClassificadorCategorias
from mercadolivre.highlights import CategoriaHighlightsInvalida, Highlights
from mercadolivre.trends import Trends

INTERVALO_SEGUNDOS = 60 * 60
META_POR_GRUPO = 30
_LOCK_COLETA = threading.Lock()

FONTES_DE_COLETA = {
    "Celulares": {"categoria_id": "MLB1055", "grupos": ("Celulares",)},
    "Games": {"categoria_id": "MLB1144", "grupos": ("Games",)},
    "Tecnologia": {"categoria_id": "MLB1648", "grupos": ("Tecnologia",)},
    "Casa": {"categoria_id": "MLB1574", "grupos": ("Casa",)},
    "Esportes": {"categoria_id": "MLB264201", "grupos": ("Esportes",)},
    "Moda": {"categoria_id": "MLB1430", "grupos": ("Moda Feminina", "Moda Masculina")},
    "Beleza e Cuidados": {"categoria_id": "MLB1246", "grupos": ("Beleza e Cuidados",)},
}

MAX_CATEGORIAS_POR_FONTE = 40
MAX_NIVEIS_SUBCATEGORIAS = 3
CATEGORIAS_HIGHLIGHTS_INVALIDAS = {"MLB11207", "MLB1902", "MLB459667"}


def coletar_tendencias():
    print("\n" + "=" * 70 + "\nCOLETANDO TENDÊNCIAS\n" + "=" * 70)
    tendencias = Trends().buscar()
    if not tendencias:
        print("Nenhuma tendência retornada.")
        return 0

    desativar_todas()
    salvas = 0
    for posicao, tendencia in enumerate(tendencias, start=1):
        if isinstance(tendencia, str):
            palavra, url, posicao_api = tendencia, None, posicao
        elif isinstance(tendencia, dict):
            palavra = tendencia.get("keyword") or tendencia.get("palavra") or tendencia.get("name") or tendencia.get("query")
            url = tendencia.get("url")
            posicao_api = tendencia.get("position") or tendencia.get("posicao") or posicao
        else:
            continue
        if palavra:
            salvar_tendencia(palavra=palavra, url=url, posicao=posicao_api)
            salvas += 1

    print(f"Tendências recebidas: {len(tendencias)}")
    print(f"Tendências salvas: {salvas}")
    return salvas


def montar_fontes(categorias_api, nome_fonte, categoria_id):
    fontes = [{"id": categoria_id, "nome": nome_fonte, "principal": True, "nivel": 0}]
    for categoria in categorias_api.descendentes(
        categoria_id,
        max_niveis=MAX_NIVEIS_SUBCATEGORIAS,
        limite=MAX_CATEGORIAS_POR_FONTE - 1,
    ):
        cid = str(categoria["id"])
        nome = str(categoria.get("name") or cid).strip()
        if nome.lower() == "outros" or cid in CATEGORIAS_HIGHLIGHTS_INVALIDAS:
            continue
        fontes.append({"id": cid, "nome": nome, "principal": False, "nivel": categoria.get("nivel", 1)})
        if len(fontes) >= MAX_CATEGORIAS_POR_FONTE:
            break

    # Muda o ponto inicial das subcategorias a cada hora.
    if len(fontes) > 2:
        principal, subs = fontes[0], fontes[1:]
        deslocamento = int(time.time() // INTERVALO_SEGUNDOS) % len(subs)
        fontes = [principal, *subs[deslocamento:], *subs[:deslocamento]]
    return fontes


def metas_concluidas(grupos, progresso):
    return all(progresso[g] >= META_POR_GRUPO for g in grupos)


def processar_produtos(produtos, classificador, grupos, progresso, ids_processados):
    resumo = {k: 0 for k in (
        "recebidos", "novos", "existentes", "sem_nome", "sem_categoria",
        "fora", "duplicados", "erros"
    )}
    resumo["recebidos"] = len(produtos)

    for produto in produtos:
        if metas_concluidas(grupos, progresso):
            break
        if not isinstance(produto, dict):
            resumo["fora"] += 1
            continue

        ml_id = produto.get("id")
        tipo = produto.get("tipo")
        nome = produto.get("nome")
        categoria_id = produto.get("category_id")
        if not ml_id or not tipo:
            resumo["fora"] += 1
            continue

        chave = str(ml_id)
        if chave in ids_processados:
            resumo["duplicados"] += 1
            continue
        ids_processados.add(chave)

        if not nome:
            resumo["sem_nome"] += 1
            continue
        if not categoria_id:
            resumo["sem_categoria"] += 1
            continue

        grupo = classificador.classificar(categoria_id=categoria_id, titulo=nome)
        if grupo not in grupos or progresso[grupo] >= META_POR_GRUPO:
            resumo["fora"] += 1
            continue

        oportunidade = {
            "id": ml_id,
            "tipo": tipo,
            "nome": nome,
            "imagem": produto.get("imagem"),
            "ranking": produto.get("ranking"),
            "category_id": categoria_id,
        }
        try:
            novo = salvar_oportunidade(
                produto=oportunidade,
                fonte="highlights",
                categoria=grupo,
                origem="mercadolivre",
            )
            if novo:
                progresso[grupo] += 1
                resumo["novos"] += 1
            else:
                resumo["existentes"] += 1
        except Exception as erro:
            resumo["erros"] += 1
            print(f"    Erro ao salvar {ml_id}: {erro}")

    return resumo


def coletar_highlights():
    print("\n" + "=" * 70 + "\nCOLETANDO HIGHLIGHTS\n" + "=" * 70)
    print(f"Meta: {META_POR_GRUPO} novas oportunidades por grupo")

    highlights = Highlights(tentativas=3, espera_inicial=3)
    categorias_api = CategoriasMercadoLivre(highlights.client)
    classificador = ClassificadorCategorias(categorias_api)

    grupos = []
    for cfg in FONTES_DE_COLETA.values():
        grupos.extend(cfg["grupos"])
    progresso = {grupo: 0 for grupo in grupos}
    ids_processados = set()
    totais = {k: 0 for k in (
        "consultas", "invalidas", "recebidos", "novos", "existentes",
        "sem_nome", "sem_categoria", "fora", "duplicados", "erros"
    )}

    for nome_fonte, cfg in FONTES_DE_COLETA.items():
        grupos_fonte = cfg["grupos"]
        print("\n" + "#" * 70)
        print(f"FONTE: {nome_fonte}")
        print("Metas: " + ", ".join(f"{g} {progresso[g]}/{META_POR_GRUPO}" for g in grupos_fonte))
        print("#" * 70)

        fontes = montar_fontes(categorias_api, nome_fonte, cfg["categoria_id"])
        print(f"Categorias disponíveis: {len(fontes)}")

        for fonte in fontes:
            if metas_concluidas(grupos_fonte, progresso):
                print("  ✅ Meta da fonte atingida. Próxima fonte.")
                break
            if fonte["id"] in CATEGORIAS_HIGHLIGHTS_INVALIDAS:
                continue

            totais["consultas"] += 1
            tipo = "Principal" if fonte["principal"] else f"Subcategoria N{fonte['nivel']}"
            print(f"\n  [{tipo}] {fonte['nome']} ({fonte['id']})")

            try:
                produtos = highlights.buscar(fonte["id"])
            except CategoriaHighlightsInvalida as erro:
                CATEGORIAS_HIGHLIGHTS_INVALIDAS.add(fonte["id"])
                totais["invalidas"] += 1
                print(f"    Categoria ignorada: {erro}")
                continue
            except Exception as erro:
                totais["erros"] += 1
                print(f"    Erro ao buscar: {erro}")
                continue

            if not produtos:
                print("    Nenhum produto retornado após as tentativas.")
                continue

            r = processar_produtos(produtos, classificador, grupos_fonte, progresso, ids_processados)
            for chave in ("recebidos", "novos", "existentes", "sem_nome", "sem_categoria", "fora", "duplicados", "erros"):
                totais[chave] += r[chave]

            print(f"    Recebidos: {r['recebidos']}")
            print(f"    Novos: {r['novos']}")
            print(f"    Já existentes/recentes: {r['existentes']}")
            print(f"    Sem nome: {r['sem_nome']}")
            print(f"    Sem category_id: {r['sem_categoria']}")
            print(f"    Fora dos grupos: {r['fora']}")
            print(f"    Duplicados nesta coleta: {r['duplicados']}")
            print("    Progresso: " + ", ".join(f"{g} {progresso[g]}/{META_POR_GRUPO}" for g in grupos_fonte))

        for grupo in grupos_fonte:
            if progresso[grupo] < META_POR_GRUPO:
                print(f"  ⚠️ {grupo}: faltaram {META_POR_GRUPO - progresso[grupo]} para a meta.")

    print("\n" + "=" * 70 + "\nRESUMO FINAL DOS HIGHLIGHTS\n" + "=" * 70)
    for grupo, qtd in progresso.items():
        print(f"{'✅' if qtd >= META_POR_GRUPO else '⚠️'} {grupo}: {qtd}/{META_POR_GRUPO}")
    print("-" * 70)
    print(f"Consultas realizadas: {totais['consultas']}")
    print(f"Categorias inválidas ignoradas: {totais['invalidas']}")
    print(f"Produtos recebidos: {totais['recebidos']}")
    print(f"Novas oportunidades: {totais['novos']}")
    print(f"Já existentes/recentes: {totais['existentes']}")
    print(f"Sem nome: {totais['sem_nome']}")
    print(f"Sem category_id: {totais['sem_categoria']}")
    print(f"Fora dos grupos: {totais['fora']}")
    print(f"Duplicados na mesma coleta: {totais['duplicados']}")
    print(f"Erros: {totais['erros']}")
    return totais["novos"]


def executar_coleta():
    if not _LOCK_COLETA.acquire(blocking=False):
        print("⏳ Coleta ignorada: já existe outra coleta em andamento neste processo.")
        return 0
    try:
        print("\n" + "=" * 70 + "\nPROMOCONN - COLETA AUTOMÁTICA\n" + "=" * 70)
        try:
            coletar_tendencias()
        except Exception as erro:
            print(f"Erro geral nas tendências: {erro}")
        try:
            return coletar_highlights()
        except Exception as erro:
            print(f"Erro geral nos highlights: {erro}")
            return 0
    finally:
        _LOCK_COLETA.release()


def executar_worker():
    criar_tabelas()
    print("\n" + "=" * 70 + "\nPROMOCONN COLETOR WORKER\n" + "=" * 70)
    print("Intervalo de coleta: 1 hora")
    print(f"Meta por grupo: {META_POR_GRUPO} novas oportunidades")
    while True:
        executar_coleta()
        print("\nPróxima coleta em 1 hora.\n")
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    executar_worker()
