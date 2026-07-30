# PromoConn — atualização do banco

Este pacote corrige o erro:

```text
column "origem" does not exist
```

## Arquivos

Copie para a pasta `database/`:

- `database.py`
- `migrator.py`
- `schema.sql`
- `migration.sql`
- `oportunidades.py`
- `historico_publicacoes.py`

## Inicialização

A aplicação já pode continuar chamando:

```python
from database.database import criar_tabelas

criar_tabelas()
```

A função agora:

1. cria tabelas ausentes;
2. adiciona colunas ausentes;
3. preenche `origem = 'mercadolivre'` nos registros antigos;
4. cria os índices necessários.

## Teste de sintaxe

```bash
python -m py_compile database/database.py database/migrator.py database/oportunidades.py database/historico_publicacoes.py
```

## Git

```bash
git add database/database.py database/migrator.py database/schema.sql database/migration.sql database/oportunidades.py database/historico_publicacoes.py
git commit -m "Adiciona migrações automáticas ao PostgreSQL"
git push origin main
```

## Importante

Não apague o banco. A migração foi criada para preservar os dados existentes.
