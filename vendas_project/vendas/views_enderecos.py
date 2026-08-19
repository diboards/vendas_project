# vendas/views_enderecos.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import EnderecoEntrega, CarrinhoItem, ProdutoVariacao
from .forms import EnderecoEntregaForm
from django.db import IntegrityError



@login_required
def meus_enderecos(request):
    """Página principal de gerenciamento de endereços"""
    enderecos = EnderecoEntrega.objects.filter(usuario=request.user).order_by('-principal', '-id')
    
    context = {
        'enderecos': enderecos,
        'total_enderecos': enderecos.count(),
    }
    return render(request, 'vendas/meus_enderecos.html', context)

# vendas/views_enderecos.py

@login_required
@require_http_methods(["POST"])
def adicionar_ou_editar_endereco(request):
    """Adiciona ou edita um endereço via AJAX"""
    try:
        endereco_id = request.POST.get('endereco_id')
        
        # Validação dos campos obrigatórios
        rua = request.POST.get('rua')
        numero = request.POST.get('numero')
        bairro = request.POST.get('bairro')
        cidade = request.POST.get('cidade')
        estado = request.POST.get('estado')
        cep = request.POST.get('cep')
        
        # Log para debug
        print(f"DEBUG - endereco_id: {endereco_id}")
        print(f"DEBUG - Dados recebidos: rua={rua}, numero={numero}, bairro={bairro}, cidade={cidade}, estado={estado}, cep={cep}")
        
        if not all([rua, numero, bairro, cidade, estado, cep]):
            return JsonResponse({
                'success': False,
                'error': 'Todos os campos obrigatórios devem ser preenchidos.'
            })
        
        principal = request.POST.get('principal') == 'on'
        complemento = request.POST.get('complemento', '')
        
        if endereco_id and endereco_id != '':
            # ===== MODO EDITAR =====
            endereco = get_object_or_404(EnderecoEntrega, id=endereco_id, usuario=request.user)
            
            # Atualiza os campos
            endereco.rua = rua
            endereco.numero = numero
            endereco.complemento = complemento
            endereco.bairro = bairro
            endereco.cidade = cidade
            endereco.estado = estado
            endereco.cep = cep
            
            if principal:
                # Remove principal de outros endereços
                EnderecoEntrega.objects.filter(usuario=request.user, principal=True).update(principal=False)
                endereco.principal = True
            else:
                endereco.principal = False
            
            endereco.save()
            message = 'Endereço atualizado com sucesso!'
            print(f"DEBUG - Endereço {endereco_id} atualizado com sucesso")
            
        else:
            # ===== MODO ADICIONAR =====
            if principal:
                EnderecoEntrega.objects.filter(usuario=request.user, principal=True).update(principal=False)
            
            endereco = EnderecoEntrega(
                usuario=request.user,
                cep=cep,
                rua=rua,
                numero=numero,
                complemento=complemento,
                bairro=bairro,
                cidade=cidade,
                estado=estado,
                principal=principal if principal else not EnderecoEntrega.objects.filter(usuario=request.user).exists()
            )
            endereco.save()
            message = 'Endereço adicionado com sucesso!'
            print(f"DEBUG - Novo endereço criado com ID {endereco.id}")
        
        return JsonResponse({
            'success': True,
            'message': message,
            'endereco_id': endereco.id
        })
        
    except Exception as e:
        print(f"DEBUG - Erro: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["POST"])
def deletar_endereco(request, endereco_id):
    """Remove um endereço"""
    endereco = get_object_or_404(EnderecoEntrega, id=endereco_id, usuario=request.user)
    
    # Se for o endereço principal, não pode deletar
    if endereco.principal:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Não é possível excluir o endereço principal. Defina outro como principal primeiro.'
            }, status=400)
        
        messages.error(request, 'Não é possível excluir o endereço principal. Defina outro como principal primeiro.')
        return redirect('meus_enderecos')
    
    endereco.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Endereço excluído com sucesso!'
        })
    
    messages.success(request, 'Endereço excluído com sucesso!')
    return redirect('meus_enderecos')



@login_required
@require_http_methods(["POST"])
def definir_principal(request, endereco_id):
    """Define um endereço como principal"""
    try:
        # Busca o endereço que será o principal
        endereco = get_object_or_404(EnderecoEntrega, id=endereco_id, usuario=request.user)
        
        print(f"DEBUG - Usuário: {request.user.username}")
        print(f"DEBUG - Endereço ID {endereco_id} - Antes: principal={endereco.principal}")
        
        # Método 1: Usando update direto no banco
        # Remove principal de TODOS os endereços deste usuário
        atualizados = EnderecoEntrega.objects.filter(usuario=request.user).update(principal=False)
        print(f"DEBUG - {atualizados} endereços tiveram principal removido")
        
        # Define o novo endereço como principal
        endereco.principal = True
        endereco.save(update_fields=['principal'])
        
        # Verifica se salvou corretamente
        verificado = EnderecoEntrega.objects.get(id=endereco_id)
        print(f"DEBUG - Depois: Endereço {endereco_id} principal={verificado.principal}")
        
        # Retorna sucesso
        return JsonResponse({
            'success': True,
            'message': 'Endereço principal definido com sucesso!',
            'endereco_id': endereco.id
        })
        
    except Exception as e:
        print(f"DEBUG - Erro: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
        
@login_required
def listar_enderecos_api(request):
    """API para listar endereços (usado no checkout)"""
    enderecos = EnderecoEntrega.objects.filter(usuario=request.user).order_by('-principal', '-id')
    
    enderecos_data = [{
        'id': e.id,
        'rua': e.rua,
        'numero': e.numero,
        'complemento': e.complemento,
        'bairro': e.bairro,
        'cidade': e.cidade,
        'estado': e.estado,
        'cep': e.cep,
        'principal': e.principal,
        'endereco_completo': f"{e.rua}, {e.numero} - {e.bairro}, {e.cidade}/{e.estado}"
    } for e in enderecos]
    
    return JsonResponse({
        'success': True,
        'enderecos': enderecos_data,
        'total': enderecos.count()
    })

# vendas/views/enderecos.py

@login_required
def adicionar_endereco_checkout(request):
    """View para adicionar endereço (AJAX)"""
    if request.method == 'POST':
        try:
            # Verifica se é para adicionar ou editar
            endereco_id = request.POST.get('endereco_id')
            
            if endereco_id:
                # ===== MODO EDITAR =====
                endereco = get_object_or_404(Endereco, id=endereco_id, usuario=request.user)
                
                endereco.rua = request.POST.get('rua')
                endereco.numero = request.POST.get('numero')
                endereco.complemento = request.POST.get('complemento', '')
                endereco.bairro = request.POST.get('bairro')
                endereco.cidade = request.POST.get('cidade')
                endereco.estado = request.POST.get('estado')
                endereco.cep = request.POST.get('cep')
                
                principal = request.POST.get('principal') == 'on'
                
                if principal:
                    # Remove principal de outros endereços
                    Endereco.objects.filter(usuario=request.user, principal=True).update(principal=False)
                    endereco.principal = True
                else:
                    endereco.principal = False
                
                endereco.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Endereço atualizado com sucesso!'
                })
                
            else:
                # ===== MODO ADICIONAR =====
                principal = request.POST.get('principal') == 'on'
                
                # Se for principal, remove principal de outros
                if principal:
                    Endereco.objects.filter(usuario=request.user, principal=True).update(principal=False)
                
                endereco = Endereco(
                    usuario=request.user,
                    cep=request.POST.get('cep'),
                    rua=request.POST.get('rua'),
                    numero=request.POST.get('numero'),
                    complemento=request.POST.get('complemento', ''),
                    bairro=request.POST.get('bairro'),
                    cidade=request.POST.get('cidade'),
                    estado=request.POST.get('estado'),
                    principal=principal
                )
                endereco.save()
                
                return JsonResponse({
                    'success': True,
                    'endereco_id': endereco.id,
                    'message': 'Endereço adicionado com sucesso!'
                })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})


def registrar_com_endereco(request):
    # 🔥 BUSCA O CARRINHO DA CHAVE PERSISTENTE
    carrinho_salvo = request.session.get('carrinho_persistente', {})
    
    # Se não houver carrinho persistente, tenta o carrinho normal
    if not carrinho_salvo:
        carrinho_salvo = request.session.get('carrinho', {})
    
    print(f"🔍 CARRINHO ENCONTRADO: {carrinho_salvo}")
    print(f"🔍 QUANTIDADE DE ITENS: {len(carrinho_salvo)}")
    
    if request.method == 'POST':
        print("🔍 POST recebido em registrar_com_endereco")
        print("📋 Dados POST:", request.POST)
        
        # 🔥 VALIDAÇÃO MANUAL
        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip()
        cpf = request.POST.get('cpf', '').strip()
        celular = request.POST.get('celular', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        cep = request.POST.get('cep', '').strip()
        rua = request.POST.get('rua', '').strip()
        numero = request.POST.get('numero', '').strip()
        complemento = request.POST.get('complemento', '').strip()
        bairro = request.POST.get('bairro', '').strip()
        cidade = request.POST.get('cidade', '').strip()
        estado = request.POST.get('estado', '').strip()
        
        # 🔥 INICIALIZA A LISTA DE ERROS
        erros = []
        
        if not nome:
            erros.append('Nome completo é obrigatório.')
        if not email:
            erros.append('E-mail é obrigatório.')
        if not cpf:
            erros.append('CPF é obrigatório.')
        if not celular:
            erros.append('Celular é obrigatório.')
        if len(password1) < 6:
            erros.append('Senha deve ter pelo menos 6 caracteres.')
        if password1 != password2:
            erros.append('Senhas não conferem.')
        if not cep:
            erros.append('CEP é obrigatório.')
        if not rua:
            erros.append('Rua é obrigatória.')
        if not numero:
            erros.append('Número é obrigatório.')
        if not bairro:
            erros.append('Bairro é obrigatório.')
        if not cidade:
            erros.append('Cidade é obrigatória.')
        if not estado:
            erros.append('Estado é obrigatório.')
        
        # Verifica se usuário já existe
        if User.objects.filter(username=email).exists():
            erros.append('Este e-mail já está cadastrado.')
        
        # 🔥 VERIFICA SE HÁ ERROS
        if erros:
            for erro in erros:
                messages.error(request, erro)
            return render(request, 'vendas/registrar_com_endereco.html', {
                'carrinho_count': len(carrinho_salvo),
                'email': email,
                'nome': nome,
                'cpf': cpf,
                'celular': celular,
                'cep': cep,
                'rua': rua,
                'numero': numero,
                'complemento': complemento,
                'bairro': bairro,
                'cidade': cidade,
                'estado': estado,
            })
        
        # 🔥 PEGA O CARRINHO DA CHAVE PERSISTENTE
        carrinho_antigo = request.session.get('carrinho_persistente', {})
        if not carrinho_antigo:
            carrinho_antigo = request.session.get('carrinho', {})
        
        print(f"🛒 CARRINHO ANTIGO (antes de criar usuário): {carrinho_antigo}")
        print(f"🛒 QUANTIDADE DE ITENS: {len(carrinho_antigo)}")
        
        # Se passou na validação, cria o usuário
        print(f"✅ Dados válidos! Criando usuário: {email}")
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password1,
            first_name=nome
        )
        print(f"✅ Usuário criado: ID {user.id}")
        
        # Cria endereço
        endereco = EnderecoEntrega.objects.create(
            usuario=user,
            cep=cep,
            rua=rua,
            numero=numero,
            complemento=complemento,
            bairro=bairro,
            cidade=cidade,
            estado=estado,
            principal=True
        )
        print(f"✅ Endereço criado: ID {endereco.id}")
        
        # 🔥 RESTAURA O CARRINHO
        if carrinho_antigo:
            print(f"🛒 Restaurando {len(carrinho_antigo)} itens do carrinho...")
            for chave, item in carrinho_antigo.items():
                try:
                    variacao_id = item.get('variacao_id')
                    if variacao_id:
                        variacao = ProdutoVariacao.objects.get(id=variacao_id)
                        CarrinhoItem.objects.create(
                            usuario=user,
                            variacao=variacao,
                            quantidade=item.get('quantidade', 1)
                        )
                        print(f"  ✅ Item restaurado: {variacao.produto.nome}")
                except Exception as e:
                    print(f"  ❌ Erro ao restaurar item: {e}")
            
            # 🔥 LIMPA AS CHAVES DA SESSÃO
            if 'carrinho' in request.session:
                del request.session['carrinho']
            if 'carrinho_persistente' in request.session:
                del request.session['carrinho_persistente']
            print("✅ Carrinho removido da sessão")
        else:
            print("⚠️ Nenhum carrinho para restaurar")
        
        # 🔥 VERIFICA SE O CARRINHO FOI RESTAURADO
        itens_apos = CarrinhoItem.objects.filter(usuario=user)
        print(f"🛒 ITENS NO CARRINHO APÓS RESTAURAÇÃO: {itens_apos.count()}")
        for item in itens_apos:
            print(f"  - {item.variacao.produto.nome} x {item.quantidade}")
        
        if 'email_cadastro' in request.session:
            del request.session['email_cadastro']
        
        login(request, user)
        messages.success(request, 'Cadastro realizado com sucesso!')
        print("✅ Redirecionando para o carrinho...")
        return redirect('visualizar_carrinho')
    
    # GET - Mostra o formulário
    email_salvo = request.session.get('email_cadastro', '')
    print(f"📧 GET - Email salvo na sessão: {email_salvo}")
    return render(request, 'vendas/registrar_com_endereco.html', {
        'carrinho_count': len(carrinho_salvo),
        'email': email_salvo,
    })
