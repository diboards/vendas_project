# vendas/utils.py
def get_itens_carrinho(request):
    carrinho = request.session.get('carrinho', {})
    itens = []
    total = 0

    for produto_id, dados in carrinho.items():
        subtotal = dados['preco'] * dados['quantidade']
        total += subtotal
        itens.append({
            'produto_id': produto_id,
            'nome': dados['nome'],
            'preco': dados['preco'],
            'quantidade': dados['quantidade'],
            'total': subtotal,
            'imagem': dados.get('imagem'),  # se você salva a url da imagem no carrinho
        })

    return itens, total