# vendas/context_processors.py
from django.conf import settings
from .models import CarrinhoItem

def mercadopago_settings(request):
    return {
        'MERCADOPAGO_PUBLIC_KEY': getattr(settings, 'MERCADOPAGO_PUBLIC_KEY', ''),
    }

#Contador carrinho
def carrinho_count(request):
    """Retorna a quantidade de itens no carrinho para o template base"""
    if request.user.is_authenticated:
        # Usuário logado: consulta o banco
        count = CarrinhoItem.objects.filter(usuario=request.user).count()
    else:
        # Usuário não logado: consulta a sessão
        carrinho = request.session.get('carrinho', {})
        count = sum(item.get('quantidade', 0) for item in carrinho.values())
    
    return {'carrinho_count': count}    
