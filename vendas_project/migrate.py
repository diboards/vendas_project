import os
import django
from django.core.management import call_command
from django.db import connection
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendas_project.settings')
django.setup()

print("🔄 Verificando e criando coluna variacao_id...")
with connection.cursor() as cursor:
    # Verifica se a coluna existe
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='vendas_carrinhoitem' AND column_name='variacao_id';
    """)
    exists = cursor.fetchone()
    
    if not exists:
        # 🔥 CRIA A COLUNA PRIMEIRO
        cursor.execute("ALTER TABLE vendas_carrinhoitem ADD COLUMN variacao_id integer;")
        print("✅ Coluna variacao_id criada!")
        
        # 🔥 CRIA A CHAVE ESTRANGEIRA DEPOIS
        try:
            cursor.execute("""
                ALTER TABLE vendas_carrinhoitem 
                ADD CONSTRAINT fk_carrinho_variacao 
                FOREIGN KEY (variacao_id) REFERENCES vendas_produtovariacao(id);
            """)
            print("✅ Chave estrangeira criada!")
        except Exception as e:
            print(f"⚠️ Chave estrangeira não criada: {e}")
    else:
        print("✅ Coluna variacao_id já existe!")

print("🔄 Criando variação padrão...")
from vendas.models import Produto, ProdutoVariacao

produto, created = Produto.objects.get_or_create(
    nome='Produto Padrão',
    defaults={
        'descricao': 'Produto criado automaticamente para migração',
        'categoria': 'outros',
        'ativo': True
    }
)

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
# 🔥 PULA A MIGRAÇÃO PROBLEMÁTICA E APLICA O RESTANTE
call_command('migrate', 'vendas', '--fake', '0007_inicial')
call_command('migrate', interactive=False)
print("✅ Migrações aplicadas!")

print("👤 Criando superusuário...")
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@admin.com', 'admin123')
    print("✅ Superusuário criado: admin / admin123")
