from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Cria super usuário automaticamente'

    def handle(self, *args, **kwargs):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@email.com',
                password='123456'
            )
            self.stdout.write(self.style.SUCCESS('Super usuário criado!'))
        else:
            self.stdout.write('Super usuário já existe.')