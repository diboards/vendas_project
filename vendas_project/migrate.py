import os
import django
from django.core.management import call_command
from django.db import connection
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendas_project.settings')
django.setup()

print("🔄 Verificando se a tabela vendas_produtovariacao existe...")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name='vendas_produtovariacao'
        );
    """)
    exists = cursor.fetchone()[0]
    
    if not exists:
        print("⚠️ Tabela vendas_produtovariacao não existe! Criando...")
        cursor.execute("""
            CREATE TABLE vendas_produtovariacao (
                id SERIAL PRIMARY KEY,
                produto_id INTEGER NOT NULL REFERENCES vendas_produto(id),
                cor VARCHAR(20) NOT NULL,
                tamanho VARCHAR(10) NOT NULL,
                preco DECIMAL(10,2) NOT NULL,
                quantidade_estoque INTEGER NOT NULL DEFAULT 0,
                imagem VARCHAR(200)
            );
        """)
        print("✅ Tabela vendas_produtovariacao criada!")

print("🔄 Verificando se a coluna variacao_id existe...")
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
print(f"✅ Produto criado: {produto.nome}")

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

# ============================================================
# 🔥 CRIAÇÃO FORÇADA DO SUPERUSUÁRIO
# ============================================================
print("👤 Criando superusuário...")
from django.contrib.auth import get_user_model
User = get_user_model()

# Tenta criar o superusuário com tratamento de erro
try:
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@admin.com', 'admin123')
        print("✅ Superusuário criado: admin / admin123")
    else:
        # Se já existe, verifica se a senha está correta
        user = User.objects.get(username='admin')
        if not user.check_password('admin123'):
            user.set_password('admin123')
            user.save()
            print("✅ Senha do admin resetada para admin123")
        else:
            print("ℹ️ Superusuário já existe com a senha correta")
except Exception as e:
    print(f"⚠️ Erro ao criar superusuário: {e}")
    # Tenta criar novamente com um método alternativo
    try:
        User.objects.create_superuser('admin', 'admin@admin.com', 'admin123')
        print("✅ Superusuário criado (tentativa 2): admin / admin123")
    except Exception as e2:
        print(f"❌ Falha ao criar superusuário: {e2}")
