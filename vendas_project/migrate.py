# migrate.py
import os
import django
from django.core.management import call_command
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'distrito_fitness.settings')
django.setup()

print("🔄 Criando variação padrão...")
from vendas.models import Produto, ProdutoVariacao
from decimal import Decimal

# Criar um produto padrão se não existir
produto, created = Produto.objects.get_or_create(
    nome='Produto Padrão',
    defaults={
        'descricao': 'Produto criado automaticamente para migração',
        'categoria': 'outros',
        'ativo': True
    }
)

# Criar uma variação padrão
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
call_command('makemigrations', 'vendas', interactive=False)
call_command('migrate', interactive=False)
print("✅ Migrações aplicadas!")

print("👤 Criando superusuário...")
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@admin.com', 'admin123')
    print("✅ Superusuário criado: admin / admin123")
