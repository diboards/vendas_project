import os
import django
from django.core.management import call_command
from django.contrib.auth import get_user_model
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendas_project.settings')
django.setup()

print("🔄 Criando variação padrão...")
from vendas.models import Produto, ProdutoVariacao

# 🔥 CRIA UM PRODUTO PADRÃO SEM CAMPO 'preco'
produto, created = Produto.objects.get_or_create(
    nome='Produto Padrão',
    defaults={
        'descricao': 'Produto criado automaticamente para migração',
        'categoria': 'outros',
        'ativo': True
    }
)

# 🔥 CRIA UMA VARIAÇÃO PARA O PRODUTO (com preço)
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
