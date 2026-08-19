# vendas/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from vendas.views.meu_perfil import meu_perfil

# Importação correta para a pasta views (dentro da pasta)
from vendas.views import views as views_principais

# Importação correta para o arquivo views_enderecos.py (na raiz)

from vendas import views_enderecos


urlpatterns = [
    # ===== VIEWS PRINCIPAIS (pasta views/views.py) =====
    path('', views_principais.pagina_inicial, name='pagina_inicial'),
    path('index/', views_principais.pagina_inicial, name='index'),
    path('lista_vendas/', views_principais.lista_vendas, name='lista_vendas'),
    path('cadastrar_produto/', views_principais.cadastrar_produto, name='cadastrar_produto'),
    path('vendas/nova/', views_principais.nova_venda, name='nova_venda'),
    path('relatorios-pedidos/', views_principais.relatorios_pedidos, name='relatorios_pedidos'),
    path('editar/<int:venda_id>/', views_principais.editar_venda, name='editar_venda'),
    path('deletar/<int:produto_id>/', views_principais.deletar_produto, name='deletar_produto'),
    path('venda/atualizar/<int:venda_id>/', views_principais.atualizar_venda, name='atualizar_venda'),
    
    # CORRIGIDO: use views_principais em vez de vendas_views
    path('login/', views_principais.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='pagina_inicial'), name='logout'),
    path('registrar/', views_principais.registrar_usuario, name='registrar'),
    path('orcamento/', views_principais.solicitar_orcamento, name='orcamento'),
    
    path('meu-perfil/', meu_perfil, name='meu_perfil'),
    # Estoque
    path('estoque/', views_principais.estoque, name='estoque'),
    path('estoque/editar/<int:produto_id>/', views_principais.editar_produto, name='editar_produto'),
    path('estoque/cadastrar/', views_principais.cadastrar_produto, name='cadastrar_produto'),
    
    # Painel
    path('painel/pedidos/', views_principais.gerenciar_pedidos, name='gerenciar_pedidos'),
    #path('painel/pedido/<int:pedido_id>/status/', views_principais.atualizar_status_entrega, name='atualizar_status_entrega'),
    # 🔥 ADMIN - ATUALIZAR STATUS MANUALMENTE
    path('painel/pedido/<int:pedido_id>/status/', views_principais.admin_atualizar_status, name='admin_atualizar_status'),
   
    # Carrinho e produtos
    path('produto/<int:produto_id>/', views_principais.detalhes_produto, name='detalhes_produto'),
    path('carrinho/adicionar/<int:produto_id>/', views_principais.adicionar_carrinho, name='adicionar_carrinho'),
   
    path('carrinho/', views_principais.visualizar_carrinho, name='visualizar_carrinho'),
    path('carrinho/remover/<int:item_id>/', views_principais.remover_carrinho, name='remover_carrinho'),
    path('carrinho/atualizar/<int:item_id>/', views_principais.atualizar_carrinho, name='atualizar_carrinho'),
    path('carrinho/count/', views_principais.carrinho_count_api, name='carrinho_count_api'),
    
    # Checkout e pagamento
    path('calcular-frete-ajax/', views_principais.calcular_frete_ajax, name='calcular_frete_ajax'),
    path('comprar-agora/<int:produto_id>/', views_principais.comprar_agora, name='comprar_agora'),
    path('checkout/', views_principais.checkout, name='checkout'),
    path('adicionar-endereco-checkout/', views_enderecos.adicionar_endereco_checkout, name='adicionar_endereco_checkout'),
    
    path('finalizar-pedido/', views_principais.finalizar_pedido, name='finalizar_pedido'),
    path('pagamento/', views_principais.pagamento, name='pagamento'),
    path('processar-pagamento-cartao/<int:pedido_id>/', views_principais.processar_pagamento_cartao, name='processar_pagamento_cartao'),
    path('processar-pagamento-pix/<int:pedido_id>/', views_principais.processar_pagamento_pix, name='processar_pagamento_pix'),
    path('teste-conexao/', views_principais.testar_conexao_mp, name='teste_conexao'),
    path('criar-pagamento/', views_principais.criar_pagamento, name='criar_pagamento'),
    path('pagamento/sucesso/<int:pedido_id>/', views_principais.pagamento_sucesso, name='pagamento_sucesso'),
    path('pagamento/falha/<int:pedido_id>/', views_principais.pagamento_falha, name='pagamento_falha'),
    path('pagamento/pendente/<int:pedido_id>/', views_principais.pagamento_pendente, name='pagamento_pendente'),
    path('meus-pedidos/', views_principais.meus_pedidos, name='meus_pedidos'),
    path('pedido/<int:pedido_id>/', views_principais.detalhes_pedido, name='detalhes_pedido'),
    path('webhook/mercadopago/', views_principais.webhook_mercadopago, name='webhook_mercadopago'),
    path('api/verificar-pagamento/<int:pedido_id>/', views_principais.verificar_status_pagamento, name='api_verificar_pagamento'),
    path('pedido/<int:pedido_id>/verificar-status/', views_principais.verificar_status_pagamento, name='verificar_status_pagamento'),
    path('pedido/<int:pedido_id>/diagnostico/', views_principais.diagnostico_pagamento, name='diagnostico_pagamento'),
    
    # RESET DE SENHA
    path('password_reset/', auth_views.PasswordResetView.as_view(
    template_name='vendas/auth/password_reset.html',
    email_template_name='vendas/auth/password_reset_email.txt',  # versão texto
    html_email_template_name='vendas/auth/password_reset_email.html',  # HTML real
    subject_template_name='vendas/auth/password_reset_subject.txt'
    ), name='password_reset'),

    path('password_reset_done/',
     auth_views.PasswordResetDoneView.as_view(
         template_name='vendas/auth/password_reset_done.html'
     ),
     name='password_reset_done'),

    path('reset/<uidb64>/<token>/',
     auth_views.PasswordResetConfirmView.as_view(
         template_name='vendas/auth/password_reset_confirm.html'
     ),
     name='password_reset_confirm'),

    path('reset_done/',
     auth_views.PasswordResetCompleteView.as_view(
         template_name='vendas/auth/password_reset_complete.html'
     ),
     name='password_reset_complete'),
    
    # ===== VIEWS DE ENDEREÇOS (views_enderecos.py na RAIZ) =====
    path('registrar-com-endereco/', views_enderecos.registrar_com_endereco, name='registrar_com_endereco'),
    path('meus-enderecos/', views_enderecos.meus_enderecos, name='meus_enderecos'),
    path('endereco/salvar/', views_enderecos.adicionar_ou_editar_endereco, name='salvar_endereco'),
    path('endereco/deletar/<int:endereco_id>/', views_enderecos.deletar_endereco, name='deletar_endereco'),
    path('endereco/principal/<int:endereco_id>/', views_enderecos.definir_principal, name='definir_principal'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
