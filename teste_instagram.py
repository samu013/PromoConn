from services.instagram.gerador_artes import gerar_arte


produto = {
    "titulo": "Smartphone Motorola Edge 50 Fusion 5G 256GB 8GB RAM",
    "categoria": "Celulares",
    "ranking": 1,
    "preco_antigo": "2.499,90",
    "preco_atual": "1.799,90",
    "desconto": 28,
    "imagem": "https://http2.mlstatic.com/D_NQ_NP_2X_123456-MLA00000000000_000000-F.webp",
}


caminho = gerar_arte(produto)

print()
print("ARTE GERADA:")
print(caminho)