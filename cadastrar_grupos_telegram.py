from database.canais_telegram import salvar_canal


GRUPOS = [
    {
        "nome": "PromoConn | Ofertas Gerais",
        "categoria": "Geral",
        "chat_id": "-1003999876933~",
    },
    {
        "nome": "PromoConn | Celulares & Acessórios",
        "categoria": "Celulares",
        "chat_id": "-5483008853",
    },
    {
        "nome": "PromoConn | Informática & Tecnologia",
        "categoria": "Tecnologia",
        "chat_id": "-5318951564",
    },
    {
        "nome": "PromoConn | Games",
        "categoria": "Games",
        "chat_id": "-5524984964",
    },
    {
        "nome": "PromoConn | Casa & Eletrodomésticos",
        "categoria": "Casa",
        "chat_id": "-5181480504",
    },
    {
        "nome": "PromoConn | Moda Feminina",
        "categoria": "Moda Feminina",
        "chat_id": "-5461685243",
    },
    {
        "nome": "PromoConn | Moda Masculina",
        "categoria": "Moda Masculina",
        "chat_id": "-5437118200",
    },
    {
        "nome": "PromoConn | Beleza & Cuidados",
        "categoria": "Beleza",
        "chat_id": "-5324676985",
    },
    {
        "nome": "PromoConn | Esportes & Academia",
        "categoria": "Esportes",
        "chat_id": "-5580430054",
    },
]


print()
print("=" * 70)
print("CADASTRANDO GRUPOS DO TELEGRAM")
print("=" * 70)


for grupo in GRUPOS:

    salvar_canal(
        nome=grupo["nome"],
        categoria=grupo["categoria"],
        chat_id=grupo["chat_id"],
        ativo=True,
    )

    print(
        f"✅ {grupo['categoria']} "
        f"→ {grupo['nome']}"
    )


print()
print("✅ Grupos cadastrados com sucesso.")