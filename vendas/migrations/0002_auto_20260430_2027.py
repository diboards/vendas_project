from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('vendas', '0001_initial'),  # 👈 USE O QUE EXISTE AQUI
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='status_pagamento',
            field=models.CharField(max_length=20, default='pendente'),
        ),
        migrations.AddField(
            model_name='pedido',
            name='status_entrega',
            field=models.CharField(max_length=20, default='aguardando'),
        ),
    ]