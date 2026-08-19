# vendas/migrations/0008_remove_preco_manual.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('vendas', '0007_remove_preco'),  # ← Use a migração anterior
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE vendas_produto DROP COLUMN IF EXISTS preco;",
            reverse_sql="ALTER TABLE vendas_produto ADD COLUMN preco decimal(10,2);"
        ),
    ]
