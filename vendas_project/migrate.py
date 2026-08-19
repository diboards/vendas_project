import os
import django
from django.core.management import call_command
from django.db import connection
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendas_project.settings')
django.setup()

print("🔄 Removendo colunas extras da tabela vendas_produto...")
with connection.cursor() as cursor:
    # Lista de colunas que devem ser removidas
    colunas_para_remover = ['preco', 'quantidade_estoque', 'cor', 'tamanho']
    
    for coluna in colunas_para_remover:
        cursor.execute(f"""
            DO $$ 
            BEGIN 
                IF EXISTS (SELECT 1 FROM information_schema.columns 
                           WHERE table_name='vendas_produto' AND column_name='{coluna}') THEN
                    ALTER TABLE vendas_produto DROP COLUMN {coluna};
                    RAISE NOTICE 'Coluna {coluna} removida';
                END IF;
            END $$;
        """)
        print(f"✅ Coluna '{coluna}' removida (se existia)")

print("🔄 Verificando e criando coluna variacao_id...")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='vendas_carrinhoitem' AND column_name='variacao_id';
    """)
    exists = cursor.fetchone()
    
    if not exists:
        cursor.execute("ALTER TABLE vendas_carrinhoitem ADD COLUMN variacao_id integer;")
        print("✅ Coluna variacao_id criada!")
    else:
        print("✅ Coluna variacao_id já existe!")

print("🔄 Criando variação padrão...")
from vendas.models import Produto, ProdutoVariacao

# 🔥 CRIA O PRODUTO SEM CAMPOS EXTRAS
produto, created = Produto.objects.get_or_create(
    nome='Produto Padrão',
    defaults={
        'descricao': 'Produto criado automaticamente para migração',
        'categoria': 'outros',
        'ativo': True
    }
)
print(f"✅ Produto criado: {produto.nome} (ID: {produto.id})")

# 🔥 CRIA A VARIAÇÃO COM OS CAMPOS CORRETOS
variacao, created = ProdutoVariacao.objects.get_or_create(
    produto=produto,
    cor='Branco',
    tamanho='M',
    defaults={
        'preco': Decimal('49.90'),
        'quantidade_estoque': 10
    }
)
print(f"✅ Variação padrão criada com ID: {variacao.id}")

print("🔄 Executando migrações...")
call_command('migrate', interactive=False)
print("✅ Migrações aplicadas!")

print("👤 Criando superusuário...")
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@admin.com', 'admin123')
    print("✅ Superusuário criado: admin / admin123")
