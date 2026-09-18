from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from vendas.forms import PerfilForm
from vendas.models import Perfil  # ou from ..models import Perfil

@login_required
def meu_perfil(request):
    perfil, created = Perfil.objects.get_or_create(usuario=request.user)
    
    if request.method == 'POST':
        # Processa diretamente os dados do POST
        try:
            # Atualiza User
            user = request.user
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')
            user.save()
            
            # Atualiza Perfil
            perfil.telefone = request.POST.get('telefone', '')
            perfil.cpf = request.POST.get('cpf', '')
            perfil.data_nascimento = request.POST.get('data_nascimento') or None
            perfil.bio = request.POST.get('bio', '')
            perfil.save()
            
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('meu_perfil')
            
        except Exception as e:
            messages.error(request, f'Erro ao salvar: {str(e)}')
    
    # Para GET, cria o form com os dados atuais
    initial_data = {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
    }
    form = PerfilForm(instance=perfil, initial=initial_data)
    
    context = {
        'form': form,
        'perfil': perfil,
    }
    return render(request, 'vendas/meu_perfil.html', context)


