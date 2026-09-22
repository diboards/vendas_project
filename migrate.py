import os
import django
from django.core.management import call_command
from django.db import connection
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendas_project.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

print("👤 Verificando superusuário...")

if not username or not email or not password:
    print("⚠️ Variáveis do superusuário não configuradas.")
else:
    try:
        user = User.objects.filter(username=username).first()

        if not user:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            print(f"✅ Superusuário criado: {username}")
        else:
            print(f"ℹ️ Superusuário já existe: {username}")

    except Exception as e:
        print(f"⚠️ Erro ao criar superusuário: {e}")
