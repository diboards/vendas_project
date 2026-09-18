# management/commands/atualizar_pagamentos_pendentes.py
from django.core.management.base import BaseCommand
from django.conf import settings
from vendas.models import Pedido
import mercadopago

class Command(BaseCommand):
    help = 'Atualiza status de pagamentos pendentes no Mercado Pago'

    def handle(self, *args, **options):
        pedidos_pendentes = Pedido.objects.filter(
            status__in=['pendente', 'aguardando_aprovacao'],
            id_mercado_pago__isnull=False
        )
        
        self.stdout.write(f'Encontrados {pedidos_pendentes.count()} pedidos pendentes')
        
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        
        for pedido in pedidos_pendentes:
            try:
                payment_info = sdk.payment().get(pedido.id_mercado_pago)
                
                if payment_info['status'] == 200:
                    payment = payment_info['response']
                    
                    if payment['status'] == 'approved' and pedido.status != 'aprovado':
                        # Atualizar pedido
                        pedido.status = 'aprovado'
                        pedido.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✅ Pedido {pedido.id} atualizado para APROVADO'
                            )
                        )
                    else:
                        self.stdout.write(
                            f'ℹ️  Pedido {pedido.id} - Status MP: {payment["status"]}'
                        )
                        
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Erro no pedido {pedido.id}: {str(e)}')
                )