# distrito_fitness/startup.py
import os
import django
from django.core.management import call_command
from django.contrib.auth import get_user_model

def run_migrations():
    """Executa migrações e cria superusuário"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendas_project.settings')
    django.setup()
    
    print("🔄 Executando migrações...")
    try:
        call_command('makemigrations', 'vendas', interactive=False)
        call_command('migrate', interactive=False)
        print("✅ Migrações aplicadas com sucesso!")
    except Exception as e:
        print(f"⚠️ Erro nas migrações: {e}")
    
    print("👤 Criando superusuário...")
    try:
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@admin.com',
                password='admin123'
            )
            print("✅ Superusuário criado: admin / admin123")
    except Exception as e:
        print(f"⚠️ Erro ao criar superusuário: {e}")

if __name__ == '__main__':
    run_migrations()
