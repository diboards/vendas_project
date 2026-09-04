# vendas/views.py
from decimal import Decimal
from django.db.models.functions import TruncMonth
from django.utils.dateparse import parse_date
from collections import defaultdict
from django.db import IntegrityError
from datetime import datetime, timedelta
from urllib.parse import quote
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Sum, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from decimal import Decimal, InvalidOperation
# E-mail de confirmação
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
#
from django.forms import inlineformset_factory

from collections import OrderedDict
from django.http import HttpResponseBadRequest
from django.views.decorators.http import require_POST
from vendas.models import Produto, ProdutoVariacao, ImagemVariacao, Venda, CarrinhoItem, EnderecoEntrega, Pedido, ItemPedido, COR_CHOICES, TAMANHO_CHOICES
from vendas.forms import VendaForm, ProdutoForm, ProdutoVariacaoForm, ProdutoVariacaoInlineFormSet, UsuarioComEnderecoForm
from vendas.forms import OrcamentoForm  # ← Verifique esta importação
import json, os, requests, re, unicodedata, mercadopago
from django.conf import settings

from django.core.paginator import Paginator # Estoque com filtros e paginação
from django.db.models import Sum, Count, F, Q # Estoque com filtros e paginação

from vendas.utils import get_itens_carrinho

# configuração de cache
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.conf import settings
from django.core.cache import cache
from django.contrib.admin.views.decorators import staff_member_required



# vendas/views/views.py

def calcular_precos(produto_list):
    """Calcula preços para uma lista de produtos (usa primeira variação)"""
    resultado = []
    for p in produto_list:
        # Buscar a primeira variação do produto
        variacao = p.variacoes.first()
        if variacao:
            preco_pix = (variacao.preco * Decimal("0.90")).quantize(Decimal("0.01"))
            preco_parcela = (variacao.preco / Decimal("3")).quantize(Decimal("0.01"))
            resultado.append({
                "id": p.id,
                "nome": p.nome,
                "preco": variacao.preco,
                "preco_pix": preco_pix,
                "preco_parcela": preco_parcela,
                "imagem": p.imagem or (variacao.imagem if variacao.imagem else None),
                "categoria": p.categoria,
            })
    return resultado


def remover_acentos(texto):
    """Remove acentos e converte para minúsculas."""
    nfkd = unicodedata.normalize('NFKD', texto)
    return ''.join([c for c in nfkd if not unicodedata.combining(c)]).lower()

def pagina_inicial(request):
    categoria_selecionada = request.GET.get('categoria', '')
    busca = request.GET.get('busca', '').strip()

    produtos_query = Produto.objects.filter(ativo=True)

    def calcular_precos(produto_list):
        resultado = []
        for p in produto_list:
            variacao = p.variacoes.first()
            if not variacao:
                continue

            preco_pix = (variacao.preco * Decimal("0.90")).quantize(Decimal("0.01"))
            preco_parcela = (variacao.preco / Decimal("3")).quantize(Decimal("0.01"))

            imagem_url = None
            if variacao.imagem:
                try:
                    imagem_url = variacao.imagem.url.replace("http://", "https://")
                except:
                    imagem_url = None
            if not imagem_url and p.imagem:
                try:
                    imagem_url = p.imagem.url.replace("http://", "https://")
                except:
                    imagem_url = None
            if not imagem_url:
                imagem_url = 'https://placehold.co/300x200?text=Sem+Imagem'

            resultado.append({
                "id": p.id,
                "nome": p.nome,
                "descricao": p.descricao,
                "preco": variacao.preco,
                "preco_pix": preco_pix,
                "preco_parcela": preco_parcela,
                "imagem": imagem_url,
                "categoria": p.categoria,
            })
        return resultado

    # --- Lógica de busca (sem unaccent) ---
    if busca:
        # Gera variações do termo: original, sem acento, singular
        termos = []
        termos.append(busca)
        sem_acento = remover_acentos(busca)
        termos.append(sem_acento)
        if sem_acento.endswith('s'):
            termos.append(sem_acento[:-1])  # remove 's' final para singular

        # Constrói filtro OR entre todos os termos
        filtro = Q()
        for termo in termos:
            filtro |= (
                Q(nome__icontains=termo) |
                Q(descricao__icontains=termo) |
                Q(categoria__icontains=termo)
            )

        produtos_busca = produtos_query.filter(filtro).distinct().order_by('-data_cadastro')

        # Zera listas de categorias
        produtos_lancamentos = []
        produtos_promocoes = []
        produtos_conjuntos = []
        produtos_outros = []
        produtos_destaque = []
    else:
        produtos_busca = []
        produtos_lancamentos = produtos_query.filter(categoria='lancamentos')[:12]
        produtos_promocoes = produtos_query.filter(categoria='promocoes')[:12]
        produtos_conjuntos = produtos_query.filter(categoria='conjuntos')[:12]
        produtos_outros = produtos_query.filter(categoria='outros')[:12]
        produtos_destaque = produtos_query.filter(categoria='destaque')[:6]

    context = {
        'debug': settings.DEBUG,
        'busca': busca,
        'produtos_busca': calcular_precos(produtos_busca) if busca else [],
        'produtos_lancamentos': calcular_precos(produtos_lancamentos) if not busca else [],
        'produtos_promocoes': calcular_precos(produtos_promocoes) if not busca else [],
        'produtos_conjuntos': calcular_precos(produtos_conjuntos) if not busca else [],
        'produtos_outros': calcular_precos(produtos_outros) if not busca else [],
        'produtos_destaque': calcular_precos(produtos_destaque) if not busca else [],
        'categoria_selecionada': categoria_selecionada,
    }

    return render(request, 'vendas/index.html', context)


@login_required
def testar_conexao_mp(request):
    from django.conf import settings
    import mercadopago
    import requests
    
    print("=== TESTANDO CREDENCIAIS ===")
    print(f"Access Token: {settings.MERCADOPAGO_ACCESS_TOKEN}")
    print(f"Sandbox: {settings.MERCADOPAGO_SANDBOX}")
    
    # Teste DIRETO com a API
    url = "https://api.mercadopago.com/v1/payment_methods"
    headers = {
        "Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Resposta: {response.text}")
        
        if response.status_code == 200:
            print("✅ Conexão bem-sucedida!")
            return render(request, 'vendas/teste_conexao.html', {
                'status': response.status_code,
                'message': 'Conexão bem-sucedida!',
                'credencial': settings.MERCADOPAGO_ACCESS_TOKEN
            })
        else:
            print("❌ Erro na conexão")
            return render(request, 'vendas/teste_conexao.html', {
                'status': response.status_code,
                'message': response.text,
                'credencial': settings.MERCADOPAGO_ACCESS_TOKEN
            })
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return render(request, 'vendas/teste_conexao.html', {
            'error': str(e),
            'credencial': settings.MERCADOPAGO_ACCESS_TOKEN
        })


from decimal import Decimal
from collections import OrderedDict
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from ..models import Produto, ProdutoVariacao, TAMANHO_CHOICES  # 🔥 IMPORTE A CONSTANTE

@login_required
def detalhes_produto(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id, ativo=True)
    
    # 🔥 BUSCA VARIAÇÕES COM IMAGENS ADICIONAIS
    variacoes = produto.variacoes.all().prefetch_related('imagens_adicionais')
    
    if not variacoes.exists():
        messages.warning(request, 'Este produto não está disponível no momento.')
        return redirect('pagina_inicial')
    
    # --- ORGANIZAR CORES E TAMANHOS ---
    from collections import OrderedDict
    colors = OrderedDict()
    sizes_by_color = {}
    
    for var in variacoes:
        cor = var.cor
        if cor not in colors:
            # 🔥 PEGA A IMAGEM PRINCIPAL
            imagem_url = None
            if var.imagem:
                try:
                    imagem_url = var.imagem.url.replace("http://", "https://")
                except:
                    imagem_url = None
            # 🔥 SE NÃO TIVER IMAGEM PRINCIPAL, PEGA A PRIMEIRA ADICIONAL
            if not imagem_url and var.imagens_adicionais.exists():
                try:
                    imagem_url = var.imagens_adicionais.first().imagem.url.replace("http://", "https://")
                except:
                    pass
            
            colors[cor] = {
                'cor': cor,
                'cor_display': cor,
                'imagem': imagem_url,
                'imagens_adicionais': [],  # 🔥 LISTA DE IMAGENS ADICIONAIS
            }
            sizes_by_color[cor] = []
        
        # 🔥 ADICIONA AS IMAGENS ADICIONAIS
        for img in var.imagens_adicionais.all():
            try:
                img_url = img.imagem.url.replace("http://", "https://")
                if img_url not in colors[cor]['imagens_adicionais']:
                    colors[cor]['imagens_adicionais'].append(img_url)
            except:
                pass
        
        if var.tamanho not in sizes_by_color[cor]:
            sizes_by_color[cor].append(var.tamanho)
    
    # --- PREÇOS ---
    primeira_variacao = variacoes.first()
    preco = primeira_variacao.preco
    preco_pix = preco * Decimal("0.90")
    preco_parcela = preco / Decimal("3")
    
    # --- MAPEAMENTO DE TAMANHOS ---
    TAMANHO_CHOICES_DICT = dict(TAMANHO_CHOICES)
    tamanhos_disponiveis = []
    for val, label in TAMANHO_CHOICES_DICT.items():
        existe = any(val in sizes for sizes in sizes_by_color.values())
        tamanhos_disponiveis.append({
            'valor': val,
            'label': label,
            'disponivel': existe
        })
    
    context = {
        'produto': produto,
        'variacoes': variacoes,
        'preco': preco,
        'preco_pix': preco_pix.quantize(Decimal("0.01")),
        'preco_parcela': preco_parcela.quantize(Decimal("0.01")),
        'cores_com_imagem': list(colors.values()),
        'tamanhos_disponiveis': tamanhos_disponiveis,
        'sizes_by_color': sizes_by_color,
        'size_labels': TAMANHO_CHOICES_DICT,
        'primeira_variacao': primeira_variacao,
        'colors_json': json.dumps(list(colors.values())),
        'sizes_json': json.dumps(sizes_by_color),
        'size_labels_json': json.dumps(TAMANHO_CHOICES_DICT),
    }
    return render(request, 'vendas/detalhes_produto.html', context)



def adicionar_carrinho(request, produto_id):
    if request.method == 'POST':
        produto = get_object_or_404(Produto, id=produto_id)

        try:
            quantidade = int(request.POST.get('quantidade', 1))
        except:
            quantidade = 1

        cor = request.POST.get('cor', '').strip()
        tamanho = request.POST.get('tamanho', '').strip()
        action = request.POST.get('action', 'carrinho')

        # Buscar a variação específica
        from ..models import ProdutoVariacao
        
        if not cor or not tamanho:
            variacao = produto.variacoes.first()
            if not variacao:
                messages.error(request, 'Este produto não está disponível.')
                return redirect('pagina_inicial')
        else:
            try:
                variacao = ProdutoVariacao.objects.get(
                    produto=produto,
                    cor=cor,
                    tamanho=tamanho
                )
            except ProdutoVariacao.DoesNotExist:
                messages.error(request, 'Produto não disponível nas opções selecionadas')
                return redirect('detalhes_produto', produto_id=produto_id)
        
        # Verificar estoque
        if variacao.quantidade_estoque < quantidade:
            messages.error(request, f'Quantidade indisponível. Estoque: {variacao.quantidade_estoque}')
            return redirect('detalhes_produto', produto_id=produto_id)
        
        # ===== SE NÃO ESTÁ LOGADO =====
        if not request.user.is_authenticated:
            carrinho = request.session.get('carrinho', {})
            
            if action == 'comprar':
                carrinho = {}
            
            # Chave única para a variação
            produto_key = f"v_{variacao.id}"
            
            if produto_key in carrinho:
                carrinho[produto_key]['quantidade'] += quantidade
            else:
                carrinho[produto_key] = {
                    'variacao_id': variacao.id,
                    'produto_nome': produto.nome,
                    'cor': variacao.cor,
                    'tamanho': variacao.tamanho,
                    'preco': float(variacao.preco),
                    'quantidade': quantidade,
                    'imagem': variacao.imagem.url if variacao.imagem else None
                }
            
            # 🔥 SALVA EM AMBOS OS LUGARES
            request.session['carrinho'] = carrinho
            request.session['carrinho_persistente'] = carrinho
            request.session.modified = True
            request.session.save()
            
            print(f"🛒 CARRINHO SALVO (adicionar_carrinho): {carrinho}")
            
            if action == 'comprar':
                return redirect('login')
            else:
                messages.success(request, f'{produto.nome} ({variacao.cor}/{variacao.tamanho}) adicionado!')
                return redirect('detalhes_produto', produto_id=produto_id)

        # ===== SE ESTÁ LOGADO =====
        if action == 'comprar':
            CarrinhoItem.objects.filter(usuario=request.user).delete()
        
        item, created = CarrinhoItem.objects.get_or_create(
            usuario=request.user,
            variacao=variacao,
            defaults={'quantidade': quantidade}
        )
        
        if not created:
            item.quantidade += quantidade
            item.save()
        
        messages.success(request, f'{produto.nome} ({variacao.cor}/{variacao.tamanho}) adicionado!')
        
        if action == 'comprar':
            return redirect('checkout')
        return redirect('detalhes_produto', produto_id=produto_id)

    return redirect('pagina_inicial')




def carrinho_count_api(request):
    try:
        # 🔥 Usuário logado → usa banco
        if request.user.is_authenticated:
            count = CarrinhoItem.objects.filter(usuario=request.user).count()
            return JsonResponse({'count': count})

        # 🔥 Usuário NÃO logado → usa sessão
        carrinho = request.session.get('carrinho_persistente', {})
        if not carrinho:
            carrinho = request.session.get('carrinho', {})

        if not isinstance(carrinho, dict):
            return JsonResponse({'count': 0})

        total = 0
        for item in carrinho.values():
            if isinstance(item, dict):
                total += int(item.get('quantidade', 0))

        return JsonResponse({'count': total})

    except Exception as e:
        print('ERRO carrinho_count_api:', str(e))
        return JsonResponse({'count': 0})



def visualizar_carrinho(request):
    """Exibe o carrinho (funciona para logados e anônimos)"""
    
    itens = []
    total = 0
    total_itens = 0
    
    # 🔥 SE O USUÁRIO ESTÁ LOGADO, BUSCA DO BANCO
    if request.user.is_authenticated:
        print(f"👤 Usuário logado: {request.user.username}")
        itens_db = CarrinhoItem.objects.filter(usuario=request.user).select_related('variacao__produto')
        
        for item_db in itens_db:
            if item_db.variacao:
                subtotal = item_db.quantidade * item_db.variacao.preco
                total += subtotal
                total_itens += item_db.quantidade
                
                itens.append({
                    'id': item_db.id,
                    'chave': f"db_{item_db.id}",
                    'variacao_id': item_db.variacao.id,
                    'produto_id': item_db.variacao.produto.id,
                    'nome': item_db.variacao.produto.nome,
                    'quantidade': item_db.quantidade,
                    'preco': float(item_db.variacao.preco),
                    'cor': item_db.variacao.cor,
                    'tamanho': item_db.variacao.tamanho,
                    'imagem': item_db.variacao.imagem.url if item_db.variacao.imagem else None,
                    'subtotal': subtotal,
                    'estoque_disponivel': item_db.variacao.quantidade_estoque,
                })
        
        print(f"🛒 ITENS NO BANCO: {len(itens)}")
    
    # 🔥 SE O USUÁRIO NÃO ESTÁ LOGADO, BUSCA DA SESSÃO
    else:
        print("👤 Usuário anônimo")
        carrinho = request.session.get('carrinho_persistente', {})
        if not carrinho:
            carrinho = request.session.get('carrinho', {})
        
        print(f"🛒 CARRINHO NA SESSÃO: {carrinho}")
        
        for chave, item in carrinho.items():
            if not isinstance(item, dict):
                continue
            
            quantidade = item.get('quantidade', 1)
            preco = item.get('preco', 0)
            subtotal = quantidade * preco
            total += subtotal
            total_itens += quantidade
            
            # Busca a variação para verificar estoque
            try:
                variacao = ProdutoVariacao.objects.get(id=item.get('variacao_id'))
                estoque_disponivel = variacao.quantidade_estoque
                nome = variacao.produto.nome
            except ProdutoVariacao.DoesNotExist:
                estoque_disponivel = 0
                nome = item.get('produto_nome', 'Produto')
            
            itens.append({
                'chave': chave,
                'id': None,
                'variacao_id': item.get('variacao_id'),
                'produto_id': item.get('produto_id'),
                'nome': nome,
                'quantidade': quantidade,
                'preco': preco,
                'cor': item.get('cor', 'Branco'),
                'tamanho': item.get('tamanho', 'M'),
                'imagem': item.get('imagem'),
                'subtotal': subtotal,
                'estoque_disponivel': estoque_disponivel,
            })
    
    context = {
        'itens_carrinho': itens,
        'total': total,
        'total_itens': total_itens,
        'carrinho_vazio': len(itens) == 0,
    }
    return render(request, 'vendas/carrinho.html', context)


@login_required
def remover_carrinho(request, item_id):
    item = get_object_or_404(CarrinhoItem, id=item_id, usuario=request.user)
    item.delete()
    messages.success(request, 'Item removido do carrinho!')
    return redirect('visualizar_carrinho')

def atualizar_carrinho(request, item_id):
    item = get_object_or_404(CarrinhoItem, id=item_id, usuario=request.user)

    # corrige o typo: 'quantidade'
    try:
        quantidade = int(request.POST.get('quantidade', 1))
    except (ValueError, TypeError):
        quantidade = 1

    if quantidade > 0:
        item.quantidade = quantidade
        item.save()
        subtotal_item = float(item.subtotal)
    else:
        # remover item se quantidade <= 0
        item.delete()
        subtotal_item = 0.0

    # recalcula total e contador
    itens = CarrinhoItem.objects.filter(usuario=request.user)
    total = float(sum(i.subtotal for i in itens))
    count = itens.count()

    # se for requisição AJAX, retorna JSON (para atualizar frontend sem reload)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'item_id': int(item_id),
            'subtotal_item': subtotal_item,
            'total': total,
            'count': count
        })

    # fallback: redireciona normalmente (caso não seja AJAX)
    messages.success(request, 'Carrinho atualizado!')
    return redirect('visualizar_carrinho')

@csrf_exempt
def calcular_frete_ajax(request):
    if request.method == 'POST':
        cep = request.POST.get('cep')
        produto_id = request.POST.get('produto_id')
        quantidade = int(request.POST.get('quantidade', 1))
        
        try:
            produto = Produto.objects.get(id=produto_id)
            subtotal = produto.preco * quantidade
            
            # Simulação de cálculo de frete
            if subtotal > 100:
                frete = 0.00
            else:
                frete = 15.00
            
            total = subtotal + frete
            
            return JsonResponse({
                'success': True,
                'frete': f'R$ {frete:.2f}',
                'total': f'R$ {total:.2f}',
                'frete_gratis': frete == 0
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Requisição inválida'})


@login_required
def comprar_agora(request, produto_id):
    if request.method == 'POST':
        produto = get_object_or_404(Produto, id=produto_id, ativo=True)
        quantidade = int(request.POST.get('quantidade', 1))
        cor = request.POST.get('cor', '').strip()
        tamanho = request.POST.get('tamanho', '').strip()
        
        # 🔥 Busca a variação específica
        if not cor or not tamanho:
            messages.error(request, 'Selecione cor e tamanho do produto.')
            return redirect('detalhes_produto', produto_id=produto_id)
        
        from ..models import ProdutoVariacao
        variacao = ProdutoVariacao.objects.filter(
            produto=produto,
            cor=cor,
            tamanho=tamanho
        ).first()
        
        if not variacao:
            messages.error(request, 'Variação do produto não encontrada.')
            return redirect('detalhes_produto', produto_id=produto_id)
        
        # 🔥 Usuário logado: salva no BANCO (usando variacao)
        # Limpa o carrinho anterior
        CarrinhoItem.objects.filter(usuario=request.user).delete()
        
        # Cria o novo item usando a variação
        CarrinhoItem.objects.create(
            usuario=request.user,
            variacao=variacao,  # ← USA A VARIAÇÃO!
            quantidade=quantidade
        )
        
        messages.success(request, f'{produto.nome} ({cor}/{tamanho}) adicionado ao carrinho!')
        return redirect('visualizar_carrinho')
    
    return redirect('detalhes_produto', produto_id=produto_id)



def comprar_agora_anonimo(request, produto_id):
    """Para usuários não logados - salva produto na sessão e redireciona para login"""
    produto = get_object_or_404(Produto, id=produto_id)
    
    quantidade = int(request.GET.get('quantidade', 1))
    cor = request.GET.get('cor', '').strip()
    tamanho = request.GET.get('tamanho', '').strip()
    
    # Buscar a variação
    variacao = ProdutoVariacao.objects.filter(
        produto=produto,
        cor=cor,
        tamanho=tamanho
    ).first()
    
    if not variacao:
        messages.error(request, 'Variação do produto não encontrada.')
        return redirect('detalhes_produto', produto_id=produto_id)
    
    # 🔥 CRIA O CARRINHO NA SESSÃO
    carrinho = {}
    chave = f"variacao_{variacao.id}"
    
    carrinho[chave] = {
        'variacao_id': variacao.id,
        'produto_id': produto.id,  # 🔥 ADICIONAR PARA FALLBACK
        'nome': produto.nome,
        'quantidade': quantidade,
        'preco': float(variacao.preco),
        'cor': cor,
        'tamanho': tamanho,
        'imagem': variacao.imagem.url if variacao.imagem else None
    }
    
    # 🔥 SALVA NA SESSÃO E GARANTE QUE FOI SALVO
    request.session['carrinho'] = carrinho
    request.session.modified = True
    request.session.save()
    
    print(f"🛒 CARRINHO SALVO NA SESSÃO: {carrinho}")
    print(f"🛒 SESSÃO COMPLETA: {dict(request.session)}")
    
    messages.info(request, 'Produto adicionado ao carrinho! Faça login para finalizar.')
    
    if request.GET.get('email'):
        request.session['email_cadastro'] = request.GET.get('email')
    
    return redirect(f'{settings.LOGIN_URL}?next=/carrinho/')
@login_required
def finalizar_pedido(request):
    if not request.user.is_authenticated:
        messages.warning(request, 'Faça login para finalizar o pedido')
        return redirect('login')
    
    itens_carrinho = CarrinhoItem.objects.filter(usuario=request.user)
    
    if not itens_carrinho.exists():
        messages.warning(request, 'Seu carrinho está vazio!')
        return redirect('pagina_inicial')
    
    # REDIRECIONE DIRETAMENTE PARA O CHECKOUT
    return redirect('checkout')


@login_required
def meus_pedidos(request):
    """Exibe pedidos do usuário (ou todos se for superusuário)"""
    
    # 🔥 Staff vê todos os pedidos
    if request.user.is_superuser:
        pedidos = Pedido.objects.all().prefetch_related(
            'itens_pedido',
            'itens_pedido__variacao',
            'itens_pedido__variacao__produto'
        ).order_by('-data_criacao')
    else:
        pedidos = Pedido.objects.filter(usuario=request.user).prefetch_related(
            'itens_pedido',
            'itens_pedido__variacao',
            'itens_pedido__variacao__produto'
        )

    for pedido in pedidos:
        status = pedido.status

        pedido.is_pendente = status in ['pendente', 'aguardando_aprovacao']
        pedido.is_aprovado = status in ['aprovado']
        pedido.is_andamento = status in ['processando', 'enviado']
        pedido.is_enviado = status == 'enviado'
        pedido.is_entregue = status == 'entregue'
        pedido.is_cancelado = status == 'cancelado'

        if pedido.is_cancelado:
            pedido.progresso = 100
        elif pedido.is_entregue:
            pedido.progresso = 100
        elif status == 'enviado':
            pedido.progresso = 80
        elif status == 'processando':
            pedido.progresso = 60
        elif pedido.is_aprovado:
            pedido.progresso = 40
        elif pedido.is_pendente:
            pedido.progresso = 20
        else:
            pedido.progresso = 0

    return render(request, 'vendas/meus_pedidos.html', {
        'pedidos': pedidos
    })

def enviar_email_confirmacao_pedido(pedido):
    """Envia e-mail de confirmação de pedido para o cliente"""
    try:
        subject = f'Mirna Boutique - Pedido #{pedido.id} confirmado!'
        
        # Renderizar template HTML
        html_message = render_to_string('vendas/emails/pedido_confirmado.html', {
            'pedido': pedido,
        })
        
        # Versão em texto simples (fallback)
        plain_message = strip_tags(html_message)
        
        # Enviar e-mail
        send_mail(
            subject=subject,
            message=plain_message,
            from_email='Mirna Boutique <mirnaboutique851@gmail.com>',
            recipient_list=[pedido.usuario.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        print(f"✅ E-mail de confirmação enviado para {pedido.usuario.email}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {str(e)}")
        return False

def enviar_notificacao_status(pedido, status_antigo=None):
    """Envia e-mail de notificação de mudança de status do pedido"""
    try:
        subject = f'Mirna Boutique - Pedido #{pedido.id} - Status atualizado!'
        
        html_message = render_to_string('vendas/emails/status_atualizado.html', {
            'pedido': pedido,
            'status_antigo': status_antigo,
        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email='Mirna Boutique <mirnaboutique851@gmail.com>',
            recipient_list=[pedido.usuario.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        print(f"✅ Notificação de status enviada para {pedido.usuario.email}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar notificação: {str(e)}")
        return False
        

# Views Checkout 
@login_required
def checkout(request):
    itens_carrinho = CarrinhoItem.objects.filter(usuario=request.user)
    
    if not itens_carrinho.exists():
        messages.warning(request, 'Seu carrinho está vazio!')
        return redirect('pagina_inicial')
    
    total = sum(item.subtotal for item in itens_carrinho)
    enderecos = EnderecoEntrega.objects.filter(usuario=request.user)
    
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if request.method == 'POST':
        print("=== DADOS RECEBIDOS NO POST ===")
        print("endereco_id:", request.POST.get('endereco_id'))
        print("metodo_pagamento:", request.POST.get('metodo_pagamento'))
        print("tipo_entrega:", request.POST.get('tipo_entrega'))
        print("is_ajax:", is_ajax)
        
        if request.POST.get('action') == 'adicionar_endereco':
            return adicionar_endereco_checkout(request)
        
        endereco_id = request.POST.get('endereco_id')
        metodo_pagamento = request.POST.get('metodo_pagamento')
        tipo_entrega = request.POST.get('tipo_entrega')
        
        if not endereco_id or not metodo_pagamento:
            if is_ajax:
                return JsonResponse({'erro': 'Endereço e método de pagamento são obrigatórios'}, status=400)
            messages.error(request, 'Por favor, selecione um endereço e método de pagamento.')
            return redirect('checkout')
        
        try:
            endereco = get_object_or_404(EnderecoEntrega, id=endereco_id, usuario=request.user)
            
            from decimal import Decimal
            frete = Decimal('15.00') if tipo_entrega == 'entrega' else Decimal('0.00')
            total_com_frete = total + frete
            
            if metodo_pagamento == 'pix':
                total_com_frete = total_com_frete * Decimal('0.90')
            
            # Criar pedido
            pedido = Pedido.objects.create(
                usuario=request.user,
                total=total_com_frete,
                endereco_entrega=endereco,
                status='pendente',
                metodo_pagamento=metodo_pagamento,
                tipo_entrega=tipo_entrega,
                frete=frete
            )
            
            print(f"Pedido criado: #{pedido.id}")
            
            # 🔥 CRIAR ITENS DO PEDIDO USANDO VARIAÇÃO
            for item_carrinho in itens_carrinho:
                if not item_carrinho.variacao:
                    print(f"⚠️ Item sem variação: {item_carrinho.id}")
                    continue
                
                ItemPedido.objects.create(
                    pedido=pedido,
                    variacao=item_carrinho.variacao,  # ← USA A VARIAÇÃO
                    quantidade=item_carrinho.quantidade,
                    preco_unitario=item_carrinho.variacao.preco  # ← PREÇO DA VARIAÇÃO
                )
                print(f"Item adicionado: {item_carrinho.variacao.produto.nome} - {item_carrinho.variacao.cor}/{item_carrinho.variacao.tamanho}")
            
            # Limpar carrinho
            itens_carrinho.delete()
            
            # 🔥 ENVIA E-MAIL DE CONFIRMAÇÃO
            enviar_email_confirmacao_pedido(pedido)
            
            if metodo_pagamento == 'pix':
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'pedido_id': pedido.id,
                        'metodo': 'pix',
                        'redirect_url': reverse('processar_pagamento_pix', args=[pedido.id])
                    })
                else:
                    return redirect('processar_pagamento_pix', pedido_id=pedido.id)
                    
            elif metodo_pagamento == 'cartao':
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'pedido_id': pedido.id,
                        'metodo': 'cartao',
                        'total': float(pedido.total)
                    })
                else:
                    return redirect('processar_pagamento_cartao', pedido_id=pedido.id)
            
        except Exception as e:
            print(f"ERRO: {str(e)}")
            import traceback
            traceback.print_exc()
            
            if is_ajax:
                return JsonResponse({'erro': str(e)}, status=500)
            messages.error(request, f'Erro ao processar pedido: {str(e)}')
            return redirect('checkout')
    
    # 🔥 PREPARAR ITENS PARA O TEMPLATE (com cor/tamanho da variação)
    itens_para_template = []
    for item in itens_carrinho:
        if item.variacao:
            itens_para_template.append({
                'id': item.id,
                'produto': item.variacao.produto,  # ← Produto
                'variacao': item.variacao,  # ← Variação
                'quantidade': item.quantidade,
                'cor_selecionada': item.variacao.cor,  # ← COR DA VARIAÇÃO
                'tamanho_selecionado': item.variacao.tamanho,  # ← TAMANHO DA VARIAÇÃO
                'subtotal': item.subtotal,
                'imagem': item.variacao.imagem.url if item.variacao.imagem else None,
            })
    
    return render(request, 'vendas/checkout.html', {
        'itens_carrinho': itens_para_template,  # ← DADOS CORRETOS
        'total': total,
        'enderecos': enderecos,
        'MERCADOPAGO_PUBLIC_KEY': settings.MERCADOPAGO_PUBLIC_KEY,
    })


@login_required
#def excluir_endereco(request, endereco_id):
   
   

@login_required
def pagamento(request):
    # Buscar o último pedido pendente do usuário
    pedido = Pedido.objects.filter(usuario=request.user, status='pendente').last()
    
    if not pedido:
        messages.warning(request, 'Nenhum pedido pendente encontrado.')
        return redirect('pagina_inicial')
    
    return render(request, 'vendas/pagamento.html', {
        'pedido': pedido
    })

def criar_token_cartao_real(numero_cartao, mes_validade, ano_validade, cvv, nome_titular="Titular Cartão"):
    """
    Gera um token REAL para o cartão usando a API do Mercado Pago - CORRIGIDA
    """
    try:
        print("🔐 GERANDO TOKEN REAL DO CARTÃO...")
        print(f"💳 Cartão: **** **** **** {numero_cartao[-4:]}")
        print(f"📅 Validade: {mes_validade}/{ano_validade}")
        print(f"👤 Titular: {nome_titular}")
        
        # ⚠️ CORREÇÃO: Usar ACCESS TOKEN, não public key
        access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None)
        if not access_token:
            print("❌ ERRO: Access Token não encontrado")
            return None
        
        print(f"🔑 Access Token: {access_token[:20]}...")
        
        # URL da API de tokens do Mercado Pago
        url = "https://api.mercadopago.com/v1/card_tokens"
        
        # Headers - ⚠️ CORREÇÃO: usar ACCESS TOKEN
        headers = {
            "Authorization": f"Bearer {access_token}",  # ✅ CORRIGIDO
            "Content-Type": "application/json",
            "User-Agent": "LojaPython/1.0"
        }
        
        # Dados do cartão
        payload = {
            "card_number": numero_cartao,
            "expiration_month": int(mes_validade),
            "expiration_year": int(ano_validade),
            "security_code": cvv,
            "cardholder": {
                "name": nome_titular
            }
        }
        
        print("📤 ENVIANDO PARA API DO MERCADO PAGO...")
        print(f"🔗 URL: {url}")
        print(f"📦 Payload: {payload}")
        
        # Fazer requisição com timeout
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"📡 RESPOSTA DA API: Status {response.status_code}")
        
        if response.status_code == 201:
            token_data = response.json()
            token = token_data.get("id")
            print(f"✅ TOKEN REAL GERADO COM SUCESSO: {token}")
            return token
        else:
            print(f"❌ ERRO NA TOKENIZAÇÃO: {response.status_code}")
            print(f"📋 Resposta completa: {response.text}")
            
            # Tentar extrair detalhes do erro
            try:
                error_details = response.json()
                print(f"🔍 Detalhes do erro: {error_details}")
                
                # Log mais detalhado para debugging
                if 'cause' in error_details:
                    for cause in error_details.get('cause', []):
                        print(f"🔍 Causa: {cause}")
                        
            except:
                print("🔍 Não foi possível ler detalhes do erro")
            
            return None
            
    except requests.exceptions.Timeout:
        print("⏰ TIMEOUT: A requisição demorou muito")
        return None
    except requests.exceptions.ConnectionError:
        print("🌐 ERRO DE CONEXÃO: Não foi possível conectar ao Mercado Pago")
        return None
    except Exception as e:
        print(f"💥 ERRO INESPERADO: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def criar_token_via_sdk(numero_cartao, mes_validade, ano_validade, cvv, nome_titular):
    """
    Método usando SDK do Mercado Pago
    """
    try:
        print("🔄 TENTANDO TOKENIZAÇÃO VIA SDK...")
        
        access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None)
        if not access_token:
            print("❌ Access Token não configurado")
            return None
        
        # Configurar SDK
        sdk = mercadopago.SDK("TEST-60559e27-fc39-4003-bafb-21deba8799fe")
        
        # Dados do cartão
        card_data = {
            "card_number": numero_cartao,
            "expiration_month": int(mes_validade),
            "expiration_year": int(ano_validade),
            "security_code": cvv,
            "cardholder": {
                "name": nome_titular
            }
        }
        
        print("📤 CRIANDO TOKEN VIA SDK...")
        token_result = sdk.card_token().create(card_data)
        
        print(f"📡 RESPOSTA SDK: Status {token_result['status']}")
        
        if token_result["status"] in [200, 201]:
            token = token_result["response"]["id"]
            print(f"✅ TOKEN GERADO VIA SDK: {token}")
            return token
        else:
            print(f"❌ ERRO NA SDK: {token_result}")
            # Log detalhado do erro
            error_response = token_result.get('response', {})
            print(f"🔍 Detalhes do erro SDK: {error_response}")
            return None
            
    except Exception as e:
        print(f"💥 ERRO NA SDK: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

@login_required
def criar_pagamento(request):
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método não permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        metodo = data.get('metodo')
        
        # Inicializar SDK do Mercado Pago
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        
        if metodo == 'pix':
            payment_data = {
                "transaction_amount": float(data.get('total', 0)),
                "description": "Compra na Loja",
                "payment_method_id": "pix",
                "payer": {
                    "email": request.user.email,
                    "first_name": request.user.first_name,
                    "last_name": request.user.last_name,
                }
            }
            
            payment_response = sdk.payment().create(payment_data)
            payment = payment_response["response"]
            
            if payment['status'] == 'pending':
                return JsonResponse({
                    'status': 'pending',
                    'payment_id': payment['id'],
                    'qr_code': payment['point_of_interaction']['transaction_data']['qr_code'],
                    'qr_code_base64': payment['point_of_interaction']['transaction_data']['qr_code_base64']
                })
                
        elif metodo == 'cartao':
            payment_data = {
                "transaction_amount": float(data.get('transaction_amount', 0)),
                "token": data.get('token'),
                "description": "Compra na Loja",
                "installments": int(data.get('installments', 1)),
                "payment_method_id": data.get('paymentMethodId'),
                "issuer_id": data.get('issuerId'),
                "payer": {
                    "email": request.user.email,
                    "identification": {
                        "type": "CPF",
                        "number": "12345678909"  # Pegar do usuário
                    }
                }
            }
            
            payment_response = sdk.payment().create(payment_data)
            payment = payment_response["response"]
            
            return JsonResponse({
                'status': payment['status'],
                'payment_id': payment['id'],
                'pedido_id': 123  # ID do seu pedido
            })
            
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)
    
    return JsonResponse({'erro': 'Método de pagamento inválido'}, status=400)

   
@login_required
def processar_pagamento_cartao(request, pedido_id):
    if request.method != "POST":
        return JsonResponse({"erro": "Método não permitido."}, status=405)
    
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
        
        print(f"\n{'='*50}")
        print(f"🔐 Processando pagamento para pedido #{pedido.id}")
        print(f"{'='*50}")
        
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        print(f"📦 Dados recebidos: {data}")
        
        token = data.get('token')
        print(f"💳 Token: {token[:30] if token else 'NÃO FORNECIDO'}...")
        
        # VALOR MÍNIMO PARA TESTE
        transaction_amount = float(data.get("transaction_amount", pedido.total))
        print(f"💰 Valor: R$ {transaction_amount}")
        
        # Se o valor for muito baixo, usar um valor mínimo
        if transaction_amount < 5.00:
            print(f"⚠️ Valor muito baixo (R$ {transaction_amount}). Usando R$ 5.00 para teste.")
            transaction_amount = 5.00
        
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        
        payment_data = {
            "transaction_amount": transaction_amount,
            "token": token,
            "description": f"Pedido #{pedido.id}",
            "installments": int(data.get("installments", 1)),
            "payment_method_id": data.get("payment_method_id"),
            "payer": {
                "email": data.get("payer", {}).get("email", request.user.email),
                "identification": {
                    "type": "CPF",
                    "number": data.get("payer", {}).get("identification", {}).get("number", "12345678909")
                }
            }
        }
        
        # issuer_id é opcional
        issuer_id = data.get("issuer_id")
        if issuer_id:
            payment_data["issuer_id"] = issuer_id
            print(f"🏦 Issuer ID: {issuer_id}")
        
        print(f"📤 Enviando para Mercado Pago: {json.dumps(payment_data, indent=2)}")
        
        payment_response = sdk.payment().create(payment_data)
        payment = payment_response["response"]
        
        print(f"📡 Resposta MP - Status: {payment.get('status')}")
        print(f"📡 Resposta completa: {json.dumps(payment, indent=2)}")
        
        # Se houve erro na API do MP
        if payment.get('status') in [400, '400'] or payment.get('error'):
            erro_msg = payment.get('message', 'Erro desconhecido')
            print(f"❌ ERRO MP: {erro_msg}")
            print(f"❌ Detalhes: {payment.get('cause', 'Sem detalhes')}")
            
            return JsonResponse({
                'status': 400,
                'message': erro_msg,
                'details': payment
            }, status=400)
        
        # Atualizar pedido
        pedido.pagamento_id = payment.get('id')
        pedido.status_pagamento = payment.get('status')
        
        if payment.get('status') == 'approved':
            pedido.status = 'pago'
        elif payment.get('status') == 'rejected':
            pedido.status = 'cancelado'
        
        pedido.save()
        
        return JsonResponse({
            'status': payment.get('status'),
            'payment_id': payment.get('id'),
            'message': payment.get('status_detail', ''),
            'pedido_id': pedido.id
        })
        
    except Exception as e:
        print(f"❌ EXCEÇÃO: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"erro": str(e), "status": "error"}, status=500)

def detectar_bandeira(numero_cartao):
    """Detecta a bandeira do cartão baseado nos primeiros dígitos"""
    if not numero_cartao:
        return "visa"  # padrão
    
    primeiro_digito = numero_cartao[0]
    
    if primeiro_digito == '4':
        return "visa"
    elif primeiro_digito == '5':
        return "master"
    elif primeiro_digito == '3':
        return "amex"
    elif primeiro_digito == '6':
        return "elo"
    else:
        return "visa"  # padrão

@login_required
def verificar_credenciais_mp(request):
    """View para verificar se as credenciais do Mercado Pago estão funcionando"""
    access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None)
    public_key = getattr(settings, 'MERCADOPAGO_PUBLIC_KEY', None)
    
    print("=== VERIFICAÇÃO DE CREDENCIAIS ===")
    print(f"Access Token: {access_token}")
    print(f"Public Key: {public_key}")
    
    if not access_token or not public_key:
        return JsonResponse({
            'status': 'error', 
            'message': 'Credenciais não configuradas'
        })
    
    # Testar conexão com a API
    try:
        sdk = mercadopago.SDK(access_token)
        
        # Tentar listar métodos de pagamento (endpoint simples)
        result = sdk.payment_methods().list()
        
        if result['status'] == 200:
            return JsonResponse({
                'status': 'success',
                'message': 'Credenciais válidas! Conexão estabelecida.',
                'payment_methods_count': len(result['response'])
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': f'Erro na API: {result}'
            })
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro de conexão: {str(e)}'
        })
    

# Detalhe do pedigo pago
@login_required
def detalhes_pedido(request, pedido_id):
    # 🔥 Staff (admin) pode ver qualquer pedido
    if request.user.is_superuser:
        pedido = get_object_or_404(Pedido, id=pedido_id)
    else:
        pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    
    itens_pedido = ItemPedido.objects.filter(pedido=pedido)
    
    return render(request, 'vendas/detalhes_pedido.html', {
        'pedido': pedido,
        'itens_pedido': itens_pedido
    })

@login_required
def processar_pagamento_pix(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    
    print(f"=== INICIANDO PIX PARA PEDIDO {pedido.id} ===")
    
    from django.conf import settings
    
    access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None)
    
    if not access_token:
        error_msg = "Access Token não encontrado no settings.py"
        context = {
            'pedido': pedido,
            'modo_desenvolvimento': True,
            'erro_exception': error_msg
        }
        return render(request, 'vendas/pagamento_pix.html', context)
    
    try:
        sdk = mercadopago.SDK(access_token)
        print("✅ SDK configurado")
        
        # DADOS MÍNIMOS PARA PIX - SEM notification_url
        payment_data = {
            "transaction_amount": float(pedido.total),
            "description": f"Pedido #{pedido.id}",
            "payment_method_id": "pix",
            "payer": {
                "email": request.user.email,
            },
            "external_reference": str(pedido.id),
        }
        
        print(f"📦 Dados do pagamento: {payment_data}")
        
        payment_response = sdk.payment().create(payment_data)
        print(f"📡 Resposta completa do MP: {payment_response}")
        
        if payment_response["status"] in [200, 201]:
            payment = payment_response["response"]
            print(f"✅ Pagamento criado! ID: {payment['id']}")
            
            # Salvar ID no pedido
            pedido.id_mercado_pago = payment["id"]
            pedido.save()
            print(f"✅ ID salvo no pedido: {pedido.id_mercado_pago}")
            
            # Verificar se tem dados do PIX
            if 'point_of_interaction' in payment and 'transaction_data' in payment['point_of_interaction']:
                pix_data = payment['point_of_interaction']['transaction_data']
                
                context = {
                    'pedido': pedido,
                    'modo_desenvolvimento': False,
                    'qr_code': pix_data.get('qr_code', ''),
                    'qr_code_base64': pix_data.get('qr_code_base64', ''),
                    'ticket_url': pix_data.get('ticket_url', ''),
                    'mp_public_key': getattr(settings, 'MERCADOPAGO_PUBLIC_KEY', ''),
                }
                
                print("🎉 PIX criado com sucesso!")
                return render(request, 'vendas/pagamento_pix.html', context)
            else:
                raise Exception("Dados do PIX não encontrados na resposta")
        else:
            error_details = payment_response.get('response', {})
            error_msg = f"Erro MP - Status {payment_response['status']}: {error_details}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
            
    except Exception as e:
        error_msg = f"Erro ao criar PIX: {str(e)}"
        print(f"💥 {error_msg}")
        
        context = {
            'pedido': pedido,
            'modo_desenvolvimento': True,
            'erro_exception': error_msg
        }
        return render(request, 'vendas/pagamento_pix.html', context)

# webhooks para receber confirmações de pagamento:   
    
@csrf_exempt  # Remove CSRF para webhook externo
def webhook_mercadopago(request):
    """
    Webhook para receber notificações do Mercado Pago
    IMPORTANTE: CSRF está desabilitado pois é chamado externamente
    """
    if request.method == 'POST':
        try:
            # Log para debug
            print("=== WEBHOOK MERCADO PAGO RECEBIDO ===")
            print("Headers:", dict(request.headers))
            
            # Verificar se é um payload JSON
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST.dict()
            
            print("Dados recebidos:", data)
            
            # Extrair ID do pagamento
            payment_id = None
            if 'data' in data and 'id' in data['data']:
                payment_id = data['data']['id']
            elif 'id' in data:
                payment_id = data['id']
            
            print(f"Payment ID recebido: {payment_id}")
            
            if payment_id:
                # Buscar pedido pelo ID do Mercado Pago
                pedido = Pedido.objects.filter(id_mercado_pago=payment_id).first()
                
                if pedido:
                    print(f"Pedido encontrado: #{pedido.id}")
                    # Consultar status atual no Mercado Pago
                    return atualizar_status_pedido(pedido)
                else:
                    print(f"Pedido não encontrado para payment_id: {payment_id}")
                    return JsonResponse({'status': 'not_found'}, status=404)
            else:
                print("Nenhum payment_id encontrado no webhook")
                return JsonResponse({'status': 'invalid_data'}, status=400)
                
        except Exception as e:
            print(f"💥 ERRO NO WEBHOOK: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'invalid_method'}, status=405)



@login_required
def diagnostico_pagamento(request, pedido_id):
    """Página de diagnóstico para verificar status do pagamento"""
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    
    # Consultar status diretamente no Mercado Pago
    status_info = {}
    try:
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        payment_info = sdk.payment().get(pedido.id_mercado_pago)
        
        if payment_info['status'] == 200:
            payment = payment_info['response']
            status_info = {
                'status_mp': payment['status'],
                'status_detail': payment.get('status_detail', ''),
                'date_approved': payment.get('date_approved', ''),
                'external_reference': payment.get('external_reference', ''),
                'order_id': payment.get('order', {}).get('id', ''),
            }
    except Exception as e:
        status_info['erro'] = str(e)
    
    context = {
        'pedido': pedido,
        'status_info': status_info,
        'webhook_url': f"{settings.SITE_URL}/webhook/mercadopago/",
    }
    
    return render(request, 'vendas/diagnostico_pagamento.html', context)    
    
# views.py - Views de callback para redirecionamento após pagamento
@login_required
def pagamento_sucesso(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)

    if pedido.status_pagamento != 'aprovado':
        pedido.status_pagamento = 'aprovado'
        pedido.status = 'aprovado'  # ✅ mantido
        # 🔥 CORRIGIDO: define status_entrega para 'preparando'
        pedido.status_entrega = 'preparando'
        pedido.save()

        # 🔥 ENVIA NOTIFICAÇÃO
        enviar_notificacao_status(pedido, status_antigo)

    CarrinhoItem.objects.filter(usuario=request.user).delete()

    return render(request, 'vendas/pagamento_sucesso.html', {'pedido': pedido})

@login_required
def pagamento_falha(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)

    pedido.status_pagamento = 'rejeitado'
    pedido.status = 'cancelado'
    pedido.status_entrega = 'cancelado'  # ✅ Adicionado
    pedido.save()

    return render(request, 'vendas/pagamento_falha.html', {'pedido': pedido})

@login_required
def pagamento_pendente(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)

    pedido.status_pagamento = 'pendente'
    pedido.status = 'pendente'
    pedido.status_entrega = 'aguardando'  # ✅ Adicionado
    pedido.save()

    return render(request, 'vendas/pagamento_pendente.html', {'pedido': pedido})
    

# vendas/views/views.py

# 🔥 REMOVA O DECORADOR @login_required da função
def atualizar_status_pedido(pedido):
    """Atualiza o status do pedido consultando o Mercado Pago"""
    try:
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        payment_info = sdk.payment().get(pedido.id_mercado_pago)

        if payment_info['status'] == 200:
            payment = payment_info['response']
            status_mp = payment['status']

            status_map = {
                'pending': 'pendente',
                'approved': 'aprovado',
                'rejected': 'rejeitado',
                'cancelled': 'rejeitado'
            }

            novo_status_pagamento = status_map.get(status_mp, 'pendente')

            if pedido.status_pagamento != novo_status_pagamento:
                pedido.status_pagamento = novo_status_pagamento

                if novo_status_pagamento == 'aprovado':
                    pedido.data_pagamento = timezone.now()
                    pedido.status_entrega = 'preparando'
                    pedido.status = 'aprovado'
                    # Limpa carrinho
                    CarrinhoItem.objects.filter(usuario=pedido.usuario).delete()
                elif novo_status_pagamento == 'pendente':
                    pedido.status_entrega = 'aguardando'
                    pedido.status = 'pendente'
                elif novo_status_pagamento == 'rejeitado':
                    pedido.status_entrega = 'cancelado'
                    pedido.status = 'cancelado'

                pedido.save()

                 # 🔥 ENVIA NOTIFICAÇÃO PARA O CLIENTE
                if status_antigo != novo_status_pagamento:
                    enviar_notificacao_status(pedido, status_antigo)
                
                return True

        return False

    except Exception as e:
        print(f"Erro ao atualizar status do pedido {pedido.id}: {e}")
        return False


# Views lista todos pedidos ADMIN

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_atualizar_status(request, pedido_id):
    """Admin atualiza o status do pedido manualmente"""
    if request.method == 'POST':
        pedido = get_object_or_404(Pedido, id=pedido_id)
        novo_status = request.POST.get('status_entrega')
        
        status_validos = ['aguardando', 'preparando', 'enviado', 'entregue', 'retirado', 'cancelado']
        
        if novo_status in status_validos:
            # 🔥 GUARDA O STATUS ANTIGO - DEFINIDO CORRETAMENTE
            status_antigo = pedido.status_entrega
            
            pedido.status_entrega = novo_status
            
            # Atualiza o status principal
            if novo_status == 'entregue':
                pedido.status = 'entregue'
            elif novo_status == 'cancelado':
                pedido.status = 'cancelado'
            elif novo_status == 'enviado':
                pedido.status = 'enviado'
            elif novo_status == 'preparando':
                pedido.status = 'processando'
            elif novo_status == 'aguardando':
                pedido.status = 'pendente'
            elif novo_status == 'retirado':
                pedido.status = 'entregue'
            
            pedido.save()

            # 🔥 ENVIA NOTIFICAÇÃO PARA O CLIENTE
            if status_antigo != novo_status:
                enviar_notificacao_status(pedido, status_antigo)
            
            messages.success(request, f'✅ Status do pedido #{pedido.id} atualizado para {pedido.get_status_entrega_display()}')
        else:
            messages.error(request, '❌ Status inválido.')
        
        return redirect('meus_pedidos')
    
    return redirect('meus_pedidos')

# vendas/views/views.py

@login_required
@user_passes_test(lambda u: u.is_superuser)
def gerenciar_pedidos(request):
    """Painel de gerenciamento de pedidos para staff"""
    pedidos = Pedido.objects.all().order_by('-data_criacao')
    
    context = {
        'pedidos': pedidos,
        'total_pedidos': pedidos.count(),
        'pedidos_pendentes': pedidos.filter(status='pendente').count(),
        'pedidos_aprovados': pedidos.filter(status='aprovado').count(),
        'pedidos_entregues': pedidos.filter(status='entregue').count(),
    }
    return render(request, 'vendas/meus_pedidos.html', context)
    
# vendas/views/views.py

@login_required
def verificar_status_pagamento(request, pedido_id):
    """Verifica o status do pagamento via AJAX"""
    try:
        # 🔥 Staff pode verificar qualquer pedido
        if request.user.is_superuser:
            pedido = get_object_or_404(Pedido, id=pedido_id)
        else:
            pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)

        print(f"🔍 Verificando pedido #{pedido_id} - Usuário: {request.user.username}")
        print(f"📋 Pedido: status={pedido.status}, status_pagamento={pedido.status_pagamento}, id_mp={pedido.id_mercado_pago}")

        if not pedido.id_mercado_pago:
            print("⚠️ Pedido sem ID do Mercado Pago")
            return JsonResponse({
                'status': 'error',
                'message': 'Pedido sem ID do Mercado Pago'
            })

        # 🔥 CHAMA A FUNÇÃO SEM DECORADOR
        try:
            atualizado = atualizar_status_pedido(pedido)
            print(f"✅ Status atualizado: {atualizado}")
        except Exception as e:
            print(f"❌ Erro ao atualizar status: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Erro ao atualizar status: {str(e)}'
            }, status=500)

        return JsonResponse({
            'status': 'success',
            'atualizado': atualizado,
            'pedido_status': pedido.status,
            'status_pagamento': pedido.status_pagamento,
            'status_entrega': pedido.status_entrega
        })

    except Pedido.DoesNotExist:
        print(f"❌ Pedido #{pedido_id} não encontrado")
        return JsonResponse({
            'status': 'error',
            'message': 'Pedido não encontrado'
        }, status=404)

    except Exception as e:
        print(f"💥 Erro ao verificar pedido #{pedido_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

# Função para verificar se o usuário é superusuário
def superuser_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Você precisa estar logado para acessar esta página.')
            return redirect('login')
        if not request.user.is_superuser:
            messages.error(request, 'Acesso restrito apenas para administradores.')
            return redirect('pagina_inicial')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# 🔥 ESTOQUE / LISTA DE PRODUTOS - 10 minutos
#@cache_page(60 * 10)
@superuser_required
def estoque(request):
    """View para gerenciamento de estoque com filtros e paginação"""
    
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('login')

    # 🔥 PARÂMETROS DE FILTRO E BUSCA
    status_filter = request.GET.get('status', '')
    categoria_filter = request.GET.get('categoria', '')
    estoque_baixo_filter = request.GET.get('estoque_baixo', '')
    busca = request.GET.get('busca', '').strip()
    ordenar = request.GET.get('ordenar', 'nome')
    ordem = request.GET.get('ordem', 'asc')

    # Query base
    produtos = Produto.objects.prefetch_related('variacoes').all()
    
    # 🔥 BUSCA POR NOME
    if busca:
        produtos = produtos.filter(nome__icontains=busca)
    
    # 🔥 FILTROS
    if status_filter == 'ativo':
        produtos = produtos.filter(ativo=True)
    elif status_filter == 'inativo':
        produtos = produtos.filter(ativo=False)
    
    if categoria_filter:
        produtos = produtos.filter(categoria=categoria_filter)
    
    # Filtro por Estoque Baixo
    if estoque_baixo_filter == 'sim':
        produtos_ids = []
        for p in produtos:
            if p.variacoes.filter(quantidade_estoque__lte=5).exists():
                produtos_ids.append(p.id)
        produtos = produtos.filter(id__in=produtos_ids)
    elif estoque_baixo_filter == 'nao':
        produtos_ids = []
        for p in produtos:
            if not p.variacoes.filter(quantidade_estoque__lte=5).exists():
                produtos_ids.append(p.id)
        produtos = produtos.filter(id__in=produtos_ids)

    # 🔥 ORDENAÇÃO
    if ordenar == 'nome':
        produtos = produtos.order_by('nome' if ordem == 'asc' else '-nome')
    elif ordenar == 'preco':
        # Ordenação por preço da primeira variação (mais complexa, será feita na lista)
        pass
    elif ordenar == 'estoque':
        # Ordenação por estoque da primeira variação
        pass

    # 🔥 CALCULAR TOTAIS
    total_produtos = Produto.objects.count()
    produtos_ativos = Produto.objects.filter(ativo=True).count()
    produtos_inativos = Produto.objects.filter(ativo=False).count()
    
    total_estoque_geral = 0
    for p in produtos:
        for variacao in p.variacoes.all():
            total_estoque_geral += variacao.quantidade_estoque

    # 🔥 PREPARAR LISTA COM DADOS DAS VARIAÇÕES
    produtos_com_precos = []
    for p in produtos:
        variacao = p.variacoes.first()
        
        imagem_url = None
        preco = 0
        estoque = 0
        cor = 'N/A'
        tamanho = 'N/A'
        
        if variacao:
            preco = variacao.preco
            estoque = variacao.quantidade_estoque
            cor = variacao.cor
            tamanho = variacao.tamanho
            
            try:
                if variacao.imagem:
                    imagem_url = variacao.imagem.url.replace("http://", "https://")
            except:
                pass
        
        if not imagem_url and p.imagem:
            try:
                imagem_url = p.imagem.url.replace("http://", "https://")
            except:
                pass
        
        if not imagem_url:
            imagem_url = "https://placehold.co/300x200?text=Sem+Imagem"
        
        produtos_com_precos.append({
            'id': p.id,
            'nome': p.nome,
            'preco': float(preco),
            'quantidade_estoque': estoque,
            'cor': cor,
            'tamanho': tamanho,
            'imagem': imagem_url,
            'categoria': p.get_categoria_display(),
            'ativo': p.ativo,
            'data_cadastro': p.data_criacao if hasattr(p, 'data_criacao') else p.data_cadastro,
            'produto_obj': p,
            'variacoes_count': p.variacoes.count(),
        })

    # 🔥 ORDENAÇÃO POR PREÇO/ESTOQUE (pós-processamento)
    if ordenar == 'preco':
        produtos_com_precos.sort(key=lambda x: x['preco'], reverse=(ordem == 'desc'))
    elif ordenar == 'estoque':
        produtos_com_precos.sort(key=lambda x: x['quantidade_estoque'], reverse=(ordem == 'desc'))

    # 🔥 PAGINAÇÃO
    paginator = Paginator(produtos_com_precos, 20)  # 20 itens por página
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # 🔥 CORES E TAMANHOS PARA O MODAL
    cores_disponiveis = []
    tamanhos_disponiveis = []
    ordem_tamanhos = {'PP': 0, 'P': 1, 'M': 2, 'G': 3, 'GG': 4, 'U': 5}
    
    for p in produtos:
        for variacao in p.variacoes.all():
            if variacao.cor not in cores_disponiveis:
                cores_disponiveis.append(variacao.cor)
            if variacao.tamanho not in tamanhos_disponiveis:
                tamanhos_disponiveis.append(variacao.tamanho)
    
    tamanhos_disponiveis.sort(key=lambda x: ordem_tamanhos.get(x, 99))

    context = {
        'page_obj': page_obj,
        'produtos': page_obj.object_list,
        'total_produtos': total_produtos,
        'produtos_ativos': produtos_ativos,
        'produtos_inativos': produtos_inativos,
        'total_estoque': total_estoque_geral,
        'cores_disponiveis': cores_disponiveis,
        'tamanhos_disponiveis': tamanhos_disponiveis,
        'busca': busca,
        'status_filter': status_filter,
        'categoria_filter': categoria_filter,
        'estoque_baixo_filter': estoque_baixo_filter,
        'ordenar': ordenar,
        'ordem': ordem,
    }

    return render(request, 'vendas/estoque.html', context)


@login_required
def editar_produto(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    
    if request.method == 'POST':
        
        print(f"📝 Editando produto: {produto.nome} (ID: {produto.id})")
        print(f"📋 POST data: {request.POST}")
        print(f"📁 FILES data: {request.FILES}")
        
        # Atualiza o produto
        produto.nome = request.POST.get('nome')
        produto.descricao = request.POST.get('descricao', '')
        produto.categoria = request.POST.get('categoria')
        produto.ativo = request.POST.get('ativo') == '1'
        produto.save()
        print(f"✅ Produto atualizado: {produto.nome}")
        
        # Exclui variações marcadas
        excluir_ids = request.POST.getlist('excluir_variacao[]')
        if excluir_ids:
            excluidas = produto.variacoes.filter(id__in=excluir_ids)
            print(f"🗑️ Excluindo {excluidas.count()} variações marcadas: {excluir_ids}")
            excluidas.delete()
        
        # Exclui imagens adicionais marcadas
        remover_imagens = request.POST.getlist('remover_imagem[]')
        if remover_imagens:
            removidas = ImagemVariacao.objects.filter(id__in=remover_imagens, variacao__produto=produto)
            print(f"🗑️ Excluindo {removidas.count()} imagens adicionais: " f"{remover_imagens}")
            removidas.delete()
        
        # Processa as variações
        variacao_ids = request.POST.getlist('variacao_id[]')
        cores = request.POST.getlist('cor[]')
        tamanhos = request.POST.getlist('tamanho[]')
        precos = request.POST.getlist('preco[]')
        estoques = request.POST.getlist('quantidade_estoque[]')
        
        print(f"📊 Dados recebidos:")
        print(f"   - Variação IDs: {variacao_ids}")
        print(f"   - Cores: {cores}")
        print(f"   - Tamanhos: {tamanhos}")
        print(f"   - Preços: {precos}")
        print(f"   - Estoques: {estoques}")
        
        # Mapeia imagens principais por índice
        imagens_principais = {}
        for key, file in request.FILES.items():
            if key.startswith('imagem_principal_'):
                try:
                    idx = int(key.split('_')[-1])
                    imagens_principais[idx] = file
                    print(f"📸 Imagem principal para índice {idx}: {file.name}")
                except Exception as e:
                    print(f"⚠️ Erro ao processar chave {key}: {e}")
        
        # MAPEIA IMAGENS ADICIONAIS POR ID DA VARIAÇÃO (existentes)
        imagens_adicionais_por_id = {}
        for key in request.FILES.keys():
            if key.startswith('imagens_adicionais_') and not key.startswith('imagens_adicionais_new_'):
                try:
                    match = re.search(r'imagens_adicionais_(\d+)\[\]', key)
                    if match:
                        var_id = int(match.group(1))
                        files = request.FILES.getlist(key)
                        if files:
                            imagens_adicionais_por_id[var_id] = files
                            print(f"📸 {len(files)} imagens adicionais para variação ID {var_id}")
                except Exception as e:
                    print(f"⚠️ Erro ao processar chave {key}: {e}")
        
        # MAPEIA IMAGENS ADICIONAIS POR ÍNDICE (novas variações)
        imagens_adicionais_novas = {}
        for key in request.FILES.keys():
            if key.startswith('imagens_adicionais_new_'):
                try:
                    match = re.search(r'imagens_adicionais_new_(\d+)\[\]', key)
                    if match:
                        idx = int(match.group(1))
                        files = request.FILES.getlist(key)
                        if files:
                            imagens_adicionais_novas[idx] = files
                            print(f"📸 {len(files)} imagens adicionais para nova variação índice {idx}")
                except Exception as e:
                    print(f"⚠️ Erro ao processar chave {key}: {e}")
        
        manter_ids = []
        novas_variacoes_criadas = 0
        
        for i in range(len(cores)):
            try:
                cor = cores[i] if i < len(cores) else ''
                tamanho = tamanhos[i] if i < len(tamanhos) else ''
                preco_str = precos[i] if i < len(precos) else '0'
                preco_str = preco_str.replace(',', '.')
                estoque = int(estoques[i]) if i < len(estoques) and estoques[i] else 0
                
                if not cor or not tamanho:
                    print(f"⚠️ Linha {i+1}: Cor ou tamanho vazio, pulando")
                    continue
                
                try:
                    preco = Decimal(preco_str) if preco_str else Decimal('0.00')
                except:
                    print(f"⚠️ Linha {i+1}: Preço inválido '{preco_str}', pulando")
                    continue
                
                if preco <= 0:
                    print(f"⚠️ Linha {i+1}: Preço inválido ({preco}), pulando")
                    continue
                
                variacao_id = variacao_ids[i] if i < len(variacao_ids) and variacao_ids[i] else None
                
                print(f"\n📦 Processando linha {i+1}: {cor}/{tamanho} - R$ {preco} - ID: {variacao_id}")
                
                if variacao_id and variacao_id != '':
                    # Atualiza variação existente
                    try:
                        variacao = ProdutoVariacao.objects.get(id=variacao_id, produto=produto)
                        variacao.cor = cor
                        variacao.tamanho = tamanho
                        variacao.preco = preco
                        variacao.quantidade_estoque = estoque
                        
                        # Atualiza imagem principal
                        if i in imagens_principais and imagens_principais[i]:
                            variacao.imagem = imagens_principais[i]
                            print(f"📸 Imagem principal atualizada para variação {variacao.id}")
                        
                        variacao.save()
                        manter_ids.append(variacao.id)
                        print(f"✅ Variação atualizada: {variacao.id}")
                        
                        # ADICIONA IMAGENS ADICIONAIS PARA VARIAÇÃO EXISTENTE
                        if variacao.id in imagens_adicionais_por_id:
                            for ordem, img in enumerate(imagens_adicionais_por_id[variacao.id]):
                                nova_imagem = ImagemVariacao.objects.create(
                                    variacao=variacao,
                                    imagem=img,
                                    ordem=variacao.imagens_adicionais.count() + ordem
                                )
                                print(f"✅ Imagem adicional salva para variação {variacao.id}")
                        
                    except ProdutoVariacao.DoesNotExist:
                        print(f"⚠️ Variação {variacao_id} não encontrada")
                        continue
                else:
                    # Cria nova variação
                    imagem_principal = imagens_principais.get(i, None)
                    
                    nova_variacao = ProdutoVariacao.objects.create(
                        produto=produto,
                        cor=cor,
                        tamanho=tamanho,
                        preco=preco,
                        quantidade_estoque=estoque,
                        imagem=imagem_principal
                    )
                    manter_ids.append(nova_variacao.id)
                    novas_variacoes_criadas += 1
                    print(f"✅ Nova variação criada: {nova_variacao.id} (índice {i})")
                    
                    # ADICIONA IMAGENS ADICIONAIS PARA NOVA VARIAÇÃO
                    if i in imagens_adicionais_novas:
                        for ordem, img in enumerate(imagens_adicionais_novas[i]):
                            ImagemVariacao.objects.create(
                                variacao=nova_variacao,
                                imagem=img,
                                ordem=ordem
                            )
                            print(f"✅ Imagem adicional salva para nova variação {nova_variacao.id}")
                    
            except Exception as e:
                print(f"❌ Erro ao processar variação {i+1}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Remove variações que não estão na lista de mantidas
        if manter_ids:
            removidas = produto.variacoes.exclude(id__in=manter_ids)
            if removidas.exists():
                print(f"🗑️ Removendo {removidas.count()} variações não listadas")
                removidas.delete()
        
        # Limpa cache
        cache.clear()
        
        print("=" * 50)
        print(f"✅ Produto atualizado com sucesso!")
        print(f"   - Variações mantidas: {len(manter_ids)}")
        print(f"   - Novas variações: {novas_variacoes_criadas}")
        print("=" * 50)
        
        messages.success(request, f'✅ Produto "{produto.nome}" atualizado com sucesso!')
        return redirect('estoque')
    
    return redirect('estoque')


# 🔥 DETALHES DO PRODUTO - 1 hora

@superuser_required
@login_required
@user_passes_test(lambda u: u.is_superuser)
def deletar_produto(request, produto_id):
    """Exclui um produto"""
    produto = get_object_or_404(Produto, id=produto_id)
    nome = produto.nome
    produto.delete()
    messages.success(request, f'Produto "{nome}" excluído com sucesso!')
    return redirect('estoque')


@superuser_required
@login_required
def cadastrar_produto(request):
    if request.method == 'POST':
        # --- VALIDAÇÃO BÁSICA ---
        nome = request.POST.get('nome', '').strip()
        if not nome:
            messages.error(request, 'O nome do produto é obrigatório.')
            return render(request, 'vendas/cadastrar_produto.html')
        
        # --- 1. CRIAR O PRODUTO BASE ---
        produto = Produto.objects.create(
            nome=nome,
            descricao=request.POST.get('descricao', ''),
            categoria=request.POST.get('categoria', 'outros'),
            ativo=True
        )
        
        # --- 2. PROCESSAR AS VARIAÇÕES ---
        cores = request.POST.getlist('cor[]')
        tamanhos = request.POST.getlist('tamanho[]')
        precos = request.POST.getlist('preco[]')
        estoques = request.POST.getlist('quantidade_estoque[]')
        imagens = request.FILES.getlist('imagem_variacao[]')
        
        # 🔥 MAPEIA AS IMAGENS ADICIONAIS POR ÍNDICE
        imagens_adicionais_por_indice = {}
        for key in request.FILES.keys():
            if key.startswith('imagens_adicionais_'):
                try:
                    # Extrai o índice do nome do campo
                    # Exemplo: imagens_adicionais_0[] → 0
                    import re
                    match = re.search(r'imagens_adicionais_(\d+)\[\]', key)
                    if match:
                        idx = int(match.group(1))
                        files = request.FILES.getlist(key)
                        if files:
                            imagens_adicionais_por_indice[idx] = files
                except Exception as e:
                    print(f"Erro ao processar chave {key}: {e}")
        
        variacoes_criadas = 0
        for i in range(len(cores)):
            preco_str = precos[i] if i < len(precos) else ''
            if not preco_str:
                continue
            
            try:
                preco = Decimal(preco_str.replace(',', '.'))
                if preco <= 0:
                    continue
                
                # Cria a variação
                variacao = ProdutoVariacao.objects.create(
                    produto=produto,
                    cor=cores[i] if i < len(cores) else 'Branco',
                    tamanho=tamanhos[i] if i < len(tamanhos) else 'M',
                    preco=preco,
                    quantidade_estoque=int(estoques[i]) if i < len(estoques) and estoques[i] else 0,
                    imagem=imagens[i] if i < len(imagens) and imagens[i] else None
                )
                
                # 🔥 SALVA AS IMAGENS ADICIONAIS DESTA VARIAÇÃO
                if i in imagens_adicionais_por_indice:
                    for ordem, img in enumerate(imagens_adicionais_por_indice[i]):
                        ImagemVariacao.objects.create(
                            variacao=variacao,
                            imagem=img,
                            ordem=ordem
                        )
                        print(f"✅ Imagem adicional {ordem+1} salva para variação {variacao.id}")
                
                variacoes_criadas += 1
            except (ValueError, TypeError) as e:
                print(f"❌ Erro na variação {i+1}: {e}")
                continue
        
        if variacoes_criadas == 0:
            produto.delete()
            messages.error(request, 'É necessário cadastrar pelo menos uma variação válida (com preço).')
            return render(request, 'vendas/cadastrar_produto.html')
        
        messages.success(request, f'Produto "{produto.nome}" cadastrado com {variacoes_criadas} variações!')
        return redirect('estoque')
    
    return render(request, 'vendas/cadastrar_produto.html')

def meus_pedidos(request):
    # 🔥 CORRIGIDO: usa 'itens_pedido__variacao__produto'
    pedidos = Pedido.objects.filter(usuario=request.user)\
        .prefetch_related(
            'itens_pedido',
            'itens_pedido__variacao',
            'itens_pedido__variacao__produto'
        )\
        .order_by('-data_criacao')

    return render(request, 'vendas/meus_pedidos.html', {
        'pedidos': pedidos
    })

# 🔥 LISTA DE VENDAS - 10 minutos (apenas para admin)
@cache_page(60 * 10)
@login_required
@user_passes_test(lambda u: u.is_superuser)
def lista_vendas(request):
    busca = request.GET.get('busca', '')
    vendas = Venda.objects.all().order_by('-data_criacao')
    
    if busca:
        vendas = vendas.filter(
            Q(produto__nome__icontains=busca) |
            Q(vendedor__username__icontains=busca)
        )
    
    total_vendas = vendas.count()
    total_concluidas = vendas.filter(status='concluida').count()
    total_pendentes = vendas.filter(status='pendente').count()
    total_valor = sum(venda.total for venda in vendas)  # ou use aggregate
    
    context = {
        'vendas': vendas,
        'total_vendas': total_vendas,
        'total_concluidas': total_concluidas,
        'total_pendentes': total_pendentes,
        'total_valor': total_valor,
        'busca': busca,
    }
    return render(request, 'vendas/lista_vendas.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def nova_venda(request):
    """View para admin criar uma venda manual"""
    
    if request.method == 'POST':
        produto_id = request.POST.get('produto')
        variacao_id = request.POST.get('variacao')
        quantidade = request.POST.get('quantidade')
        observacoes = request.POST.get('observacoes', '')
        status = request.POST.get('status', 'concluida')
        forma_pagamento = request.POST.get('forma_pagamento', 'pix')  # 🆕 ADICIONE AQUI
        
        if not produto_id or not variacao_id or not quantidade:
            messages.error(request, '❌ Produto, variação e quantidade são obrigatórios.')
            return redirect('nova_venda')
        
        try:
            quantidade = int(quantidade)
        except ValueError:
            messages.error(request, '❌ Quantidade inválida.')
            return redirect('nova_venda')
        
        variacao = get_object_or_404(ProdutoVariacao, id=variacao_id)
        
        if variacao.quantidade_estoque < quantidade:
            messages.error(request, f'❌ Estoque insuficiente. Disponível: {variacao.quantidade_estoque}')
            return redirect('nova_venda')
        
        # 🔥 CRIA A VENDA COM USUÁRIO E FORMA DE PAGAMENTO
        venda = Venda.objects.create(
            vendedor=request.user,
            produto=variacao.produto,
            variacao=variacao,
            quantidade=quantidade,
            preco_unitario=variacao.preco,
            forma_pagamento=forma_pagamento,  # 🆕 ADICIONE AQUI
            observacoes=observacoes,
            status=status
        )
        
        # Atualiza estoque
        variacao.quantidade_estoque -= quantidade
        variacao.save()
        
        messages.success(request, f'✅ Venda #{venda.id} criada com sucesso!')
        return redirect('lista_vendas')
    
    produtos = Produto.objects.filter(ativo=True)
    
    context = {
        'produtos': produtos,
        'titulo': 'Nova Venda Manual',
    }
    return render(request, 'vendas/nova_venda.html', context)
    
#api para buscar variações da nova venda
@login_required
@user_passes_test(lambda u: u.is_superuser)
def api_produto_variacoes(request, produto_id):
    """API para buscar variações de um produto"""
    produto = get_object_or_404(Produto, id=produto_id, ativo=True)
    variacoes = produto.variacoes.all()
    
    data = {
        'variacoes': [{
            'id': v.id,
            'cor': v.cor,
            'tamanho': v.tamanho,
            'preco': float(v.preco),
            'estoque': v.quantidade_estoque,
        } for v in variacoes]
    }
    
    return JsonResponse(data)
    

@cache_page(60 * 30)
@login_required
@user_passes_test(lambda u: u.is_superuser)
def relatorios_pedidos(request):
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    # Filtros de data
    data_inicio_parsed = parse_date(data_inicio) if data_inicio else None
    data_fim_parsed = parse_date(data_fim) if data_fim else None

    filtro_pedidos = Q()
    filtro_vendas = Q()
    if data_inicio_parsed:
        filtro_pedidos &= Q(data_criacao__date__gte=data_inicio_parsed)
        filtro_vendas &= Q(data_criacao__date__gte=data_inicio_parsed)
    if data_fim_parsed:
        filtro_pedidos &= Q(data_criacao__date__lte=data_fim_parsed)
        filtro_vendas &= Q(data_criacao__date__lte=data_fim_parsed)

    pedidos = Pedido.objects.filter(filtro_pedidos)
    vendas_manuais = Venda.objects.filter(filtro_vendas)

    print(f"📊 Pedidos online: {pedidos.count()}")
    print(f"📊 Vendas manuais: {vendas_manuais.count()}")

    # ==================== TOTAIS ====================
    total_pedidos_online = pedidos.count()
    total_vendas_manuais = vendas_manuais.count()
    total_geral = total_pedidos_online + total_vendas_manuais

    valor_total_online = pedidos.aggregate(total=Sum('total'))['total'] or Decimal('0')
    valor_total_manual = vendas_manuais.aggregate(
        total=Sum(F('quantidade') * F('preco_unitario'))
    )['total'] or Decimal('0')
    valor_total = valor_total_online + valor_total_manual

    # ==================== STATUS ====================
    # Pedidos online
    pedidos_pendentes = pedidos.filter(status='pendente').count()
    pedidos_aprovados = pedidos.filter(status='aprovado').count()
    pedidos_aguardando = pedidos.filter(status='aguardando_aprovacao').count()
    pedidos_processando = pedidos.filter(status='processando').count()
    pedidos_enviados = pedidos.filter(status='enviado').count()
    pedidos_entregues = pedidos.filter(status='entregue').count()
    pedidos_cancelados = pedidos.filter(status='cancelado').count()

    # Vendas manuais
    vendas_pendentes = vendas_manuais.filter(status='pendente').count()
    vendas_concluidas = vendas_manuais.filter(status='concluida').count()
    vendas_canceladas = vendas_manuais.filter(status='cancelada').count()

    # Combinar status (mapeando vendas concluídas como "entregues" e aguardando como "processando")
    total_pendentes = pedidos_pendentes + vendas_pendentes
    total_aprovados = pedidos_aprovados
    total_processando = pedidos_processando + pedidos_aguardando
    total_enviados = pedidos_enviados
    total_entregues = pedidos_entregues + vendas_concluidas
    total_cancelados = pedidos_cancelados + vendas_canceladas

    # ==================== PRODUTOS MAIS VENDIDOS ====================
    produtos = defaultdict(lambda: {'total_quantidade': 0, 'total_vendas': 0})

    online_prod = ItemPedido.objects.filter(pedido__in=pedidos).values(
        'variacao__produto__nome'
    ).annotate(
        total_quantidade=Sum('quantidade'),
        total_vendas=Count('pedido', distinct=True)
    )
    for item in online_prod:
        nome = item['variacao__produto__nome']
        produtos[nome]['total_quantidade'] += item['total_quantidade'] or 0
        produtos[nome]['total_vendas'] += item['total_vendas'] or 0

    manual_prod = vendas_manuais.values('produto__nome').annotate(
        total_quantidade=Sum('quantidade'),
        total_vendas=Count('id')
    )
    for item in manual_prod:
        nome = item['produto__nome']
        produtos[nome]['total_quantidade'] += item['total_quantidade'] or 0
        produtos[nome]['total_vendas'] += item['total_vendas'] or 0

    produtos_vendidos = [
        {'variacao__produto__nome': nome, **dados}
        for nome, dados in sorted(produtos.items(), key=lambda x: x[1]['total_quantidade'], reverse=True)[:10]
    ]

    # ==================== VENDAS POR MÊS ====================
    mes_dict = defaultdict(float)

    online_mes = pedidos.filter(status__in=['aprovado', 'entregue', 'enviado']).annotate(
        mes=TruncMonth('data_criacao')
    ).values('mes').annotate(total=Sum('total'))

    manual_mes = vendas_manuais.filter(status='concluida').annotate(
        mes=TruncMonth('data_criacao')
    ).values('mes').annotate(
        total=Sum(F('quantidade') * F('preco_unitario'))
    )

    for item in online_mes:
        if item['mes']:
            mes_dict[item['mes']] += float(item['total'] or 0)
    for item in manual_mes:
        if item['mes']:
            mes_dict[item['mes']] += float(item['total'] or 0)

    meses_ordenados = sorted(mes_dict.keys())
    meses_labels = [mes.strftime('%b/%Y') for mes in meses_ordenados]
    meses_valores = [mes_dict[mes] for mes in meses_ordenados]

    # ==================== FORMAS DE PAGAMENTO ====================
    pagamentos_labels = []
    pagamentos_valores = []

    pagamentos_online = pedidos.values('metodo_pagamento').annotate(total=Count('id')).order_by('-total')
    for item in pagamentos_online:
        label = dict(Pedido.METODO_PAGAMENTO_CHOICES).get(item['metodo_pagamento'], item['metodo_pagamento'])
        pagamentos_labels.append(label)
        pagamentos_valores.append(item['total'])

    pagamentos_manuais = vendas_manuais.values('forma_pagamento').annotate(total=Count('id'))
    for item in pagamentos_manuais:
        label = dict(Venda.FORMA_PAGAMENTO_CHOICES).get(item['forma_pagamento'], item['forma_pagamento'])
        pagamentos_labels.append(label)
        pagamentos_valores.append(item['total'])

    # ==================== CONTEXTO ====================
    context = {
        'data_inicio': request.GET.get('data_inicio', ''),
        'data_fim': request.GET.get('data_fim', ''),

        'total_pedidos': total_geral,
        'valor_total': valor_total,
        'pedidos_pendentes': total_pendentes,
        'pedidos_aprovados': total_aprovados,
        'pedidos_processando': total_processando,
        'pedidos_enviados': total_enviados,
        'pedidos_entregues': total_entregues,
        'pedidos_cancelados': total_cancelados,

        'produtos_vendidos': produtos_vendidos,

        'meses_labels': meses_labels,
        'meses_valores': meses_valores,

        'pagamentos_labels': pagamentos_labels,
        'pagamentos_valores': pagamentos_valores,
    }

    return render(request, 'vendas/relatorios_pedidos.html', context)
@login_required
@user_passes_test(lambda u: u.is_superuser)
def editar_venda(request, venda_id):
    """Edita uma venda (apenas admin)"""
    venda = get_object_or_404(Venda, id=venda_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        observacoes = request.POST.get('observacoes', '')
        venda.forma_pagamento = request.POST.get('forma_pagamento', 'pix')
        venda.save()
                
        if status in ['concluida', 'pendente', 'cancelada']:
            venda.status = status
            venda.observacoes = observacoes
            venda.save()
            messages.success(request, f'✅ Venda #{venda.id} atualizada com sucesso!')
        else:
            messages.error(request, '❌ Status inválido.')
        
        return redirect('lista_vendas')
    
    return redirect('lista_vendas')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def deletar_venda(request, venda_id):
    """Deleta uma venda (apenas admin)"""
    venda = get_object_or_404(Venda, id=venda_id)
    
    if request.method == 'POST':
        venda.delete()
        messages.success(request, f'✅ Venda #{venda.id} excluída com sucesso!')
        return redirect('lista_vendas')
    
    return redirect('lista_vendas')

@login_required
def atualizar_venda(request, venda_id):
    if request.method == 'POST':
        venda = get_object_or_404(Venda, id=venda_id)
        produto_id = request.POST.get('produto_id')
        quantidade = request.POST.get('quantidade')

        if produto_id and quantidade:
            venda.produto_id = produto_id
            venda.quantidade = int(quantidade)
            venda.total = venda.quantidade * venda.preco_unitario
            venda.save()

    return redirect('lista_vendas')

# Registrar Usuário
def registrar_usuario(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuário criado com sucesso! Faça login.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'vendas/registrar.html', {'form': form})



def login_view(request):
    # 🔥 SE O USUÁRIO JÁ ESTIVER LOGADO, REDIRECIONA
    if request.user.is_authenticated:
        return redirect('pagina_inicial')
    
    # 🔥 PEGA O CARRINHO DA SESSÃO
    carrinho_salvo = request.session.get('carrinho', {})
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        # ==========================================================
        # LOGIN
        # ==========================================================
        if form_type == 'login':
            username = request.POST.get('username')
            password = request.POST.get('password')
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                carrinho_antigo = request.session.get('carrinho', {})
                login(request, user)
                
                if carrinho_antigo:
                    for chave, item in carrinho_antigo.items():
                        try:
                            variacao_id = item.get('variacao_id')
                            if variacao_id:
                                variacao = ProdutoVariacao.objects.get(id=variacao_id)
                                CarrinhoItem.objects.get_or_create(
                                    usuario=user,
                                    variacao=variacao,
                                    defaults={'quantidade': item.get('quantidade', 1)}
                                )
                        except Exception as e:
                            print(f"Erro ao restaurar item: {e}")
                    
                    if 'carrinho' in request.session:
                        del request.session['carrinho']
                
                messages.success(request, f'Bem-vindo(a) {user.first_name or user.username}!')
                
                next_url = request.GET.get('next', 'pagina_inicial')
                if 'carrinho' in next_url:
                    return redirect('visualizar_carrinho')
                return redirect(next_url)
            else:
                messages.error(request, 'Usuário ou senha inválidos.')
        
        # ==========================================================
        # CADASTRO (CRIAR CONTA)
        # ==========================================================
        elif form_type == 'cadastro':
            email = request.POST.get('email', '').strip()
            
            if not email:
                messages.error(request, 'E-mail é obrigatório para cadastro.')
                return render(request, 'vendas/login.html')
            
            # 🔥 SALVA O EMAIL NA SESSÃO
            request.session['email_cadastro'] = email
            
            # 🔥 SALVA O CARRINHO EM UMA CHAVE PERSISTENTE
            if carrinho_salvo:
                request.session['carrinho_persistente'] = carrinho_salvo
                request.session.modified = True
                request.session.save()
                print(f"💾 CARRINHO SALVO EM 'carrinho_persistente': {carrinho_salvo}")
            else:
                print("⚠️ Nenhum carrinho para salvar")
            
            messages.info(request, 'Preencha seus dados para finalizar o cadastro.')
            return redirect('registrar_com_endereco')
    
    return render(request, 'vendas/login.html')


# vendas/views/views.py


def solicitar_orcamento(request):
    if request.method == 'POST':
        form = OrcamentoForm(request.POST)
        if form.is_valid():
            nome = form.cleaned_data['nome']
            telefone = form.cleaned_data['telefone']
            ambiente = dict(form.fields['ambiente'].choices)[form.cleaned_data['ambiente']]
            orcamento = dict(form.fields['orcamento'].choices)[form.cleaned_data['orcamento']]
            mensagem = f"""*SOLICITAÇÃO DE ORÇAMENTO*

*Nome:* {nome}
*Telefone:* {telefone}
*Ambiente a ser planejado:* {ambiente}
*Faixa de orçamento:* {orcamento}

Por favor, entre em contato para discutir este projeto."""
            return JsonResponse({'mensagem': mensagem})
        else:
            return JsonResponse({'errors': form.errors}, status=400)
    else:
        form = OrcamentoForm()
    return render(request, 'vendas/orcamento.html', {'form': form})
    
# controle de cache
def get_produtos_destaque():
    """Busca produtos em destaque com cache"""
    cache_key = 'produtos_destaque_cache'
    produtos = cache.get(cache_key)
    
    if not produtos:
        produtos = Produto.objects.filter(ativo=True, categoria='destaque')[:6]
        cache.set(cache_key, produtos, 60 * 10)  # 10 minutos
    
    return produtos

def get_categorias():
    """Busca categorias com cache"""
    cache_key = 'categorias_cache'
    categorias = cache.get(cache_key)
    
    if not categorias:
        categorias = Produto.objects.values_list('categoria', flat=True).distinct()
        cache.set(cache_key, categorias, 60 * 60)  # 1 hora
    
    return categorias
    
@staff_member_required
def limpar_cache(request):
    """Limpa todo o cache do sistema (apenas admin)"""
    try:
        cache.clear()
        messages.success(request, '✅ Cache limpo com sucesso!')
    except Exception as e:
        messages.error(request, f'❌ Erro ao limpar cache: {str(e)}')
    
    return redirect('pagina_inicial')    
