from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import requests
import mercadopago
from django.conf import settings
from vendas.models import Pedido
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Verifica o status de pagamentos pendentes no Mercado Pago'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--horas',
            type=int,
            default=24,
            help='Verificar pedidos das últimas X horas (padrão: 24)'
        )
    
    def handle(self, *args, **options):
        horas = options['horas']
        limite_tempo = timezone.now() - timedelta(hours=horas)
        
        # Buscar pedidos pendentes
        pedidos_pendentes = Pedido.objects.filter(
            status__in=['pendente', 'aguardando_aprovacao'],
            data_criacao__gte=limite_tempo,
            id_mercado_pago__isnull=False
        )
        
        self.stdout.write(f"Verificando {pedidos_pendentes.count()} pedidos pendentes das últimas {horas} horas...")
        
        # Configurar SDK do Mercado Pago
        try:
            sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        except:
            self.stdout.write(self.style.ERROR('Erro ao configurar SDK do Mercado Pago'))
            return
        
        for pedido in pedidos_pendentes:
            try:
                self.stdout.write(f"Verificando pedido #{pedido.id}...")
                
                # Consultar status no Mercado Pago
                payment_info = sdk.payment().get(pedido.id_mercado_pago)
                
                if payment_info['status'] == 200:
                    payment = payment_info['response']
                    status_mp = payment['status']
                    status_detail = payment.get('status_detail', '')
                    
                    # Mapear status do Mercado Pago para nosso sistema
                    status_map = {
                        'pending': 'pendente',
                        'approved': 'aprovado',
                        'authorized': 'aguardando_aprovacao',
                        'in_process': 'aguardando_aprovacao',
                        'in_mediation': 'aguardando_aprovacao',
                        'rejected': 'cancelado',
                        'cancelled': 'cancelado',
                        'refunded': 'cancelado',
                        'charged_back': 'cancelado'
                    }
                    
                    novo_status = status_map.get(status_mp, 'pendente')
                    
                    # Atualizar pedido se status mudou
                    if pedido.status != novo_status:
                        status_anterior = pedido.status
                        pedido.status = novo_status
                        pedido.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Pedido #{pedido.id}: {status_anterior} → {novo_status} ({status_mp})"
                            )
                        )
                        
                        # Se pagamento foi aprovado, limpar carrinho
                        if novo_status == 'aprovado':
                            from vendas.models import CarrinhoItem
                            CarrinhoItem.objects.filter(usuario=pedido.usuario).delete()
                            self.stdout.write(f"  Carrinho do usuário {pedido.usuario} limpo")
                    
                    else:
                        self.stdout.write(f"  Status mantido: {pedido.status} ({status_mp})")
                        
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Erro ao consultar pedido #{pedido.id}: {payment_info.get('response', {}).get('message', 'Erro desconhecido')}"
                        )
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Erro ao processar pedido #{pedido.id}: {str(e)}")
                )
        
        self.stdout.write(self.style.SUCCESS("Verificação de pagamentos concluída!"))