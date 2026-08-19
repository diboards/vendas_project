# vendas/admin.py
from django.contrib import admin
from .models import Produto, ProdutoVariacao, Venda, Pedido, EnderecoEntrega, Perfil


class ProdutoVariacaoInline(admin.TabularInline):
    """Exibe variações dentro do produto no admin"""
    model = ProdutoVariacao
    extra = 1
    fields = ['cor', 'tamanho', 'preco', 'quantidade_estoque', 'imagem']


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ['id', 'nome', 'categoria', 'ativo', 'get_preco_minimo', 'get_estoque_total']
    list_filter = ['categoria', 'ativo']
    search_fields = ['nome', 'descricao']
    inlines = [ProdutoVariacaoInline]
    
    def get_preco_minimo(self, obj):
        return obj.get_preco_minimo()
    get_preco_minimo.short_description = 'Preço mínimo'
    
    def get_estoque_total(self, obj):
        return obj.get_estoque_total()
    get_estoque_total.short_description = 'Estoque total'


@admin.register(ProdutoVariacao)
class ProdutoVariacaoAdmin(admin.ModelAdmin):
    list_display = ['id', 'produto', 'cor', 'tamanho', 'preco', 'quantidade_estoque', 'em_estoque']
    list_filter = ['cor', 'tamanho', 'produto__categoria']
    search_fields = ['produto__nome', 'cor', 'tamanho']
    
    def em_estoque(self, obj):
        return obj.quantidade_estoque > 0
    em_estoque.boolean = True
    em_estoque.short_description = 'Em estoque'


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ['id', 'produto', 'quantidade', 'total', 'data_venda', 'status']
    list_filter = ['status', 'data_venda']
    search_fields = ['produto__nome']
    readonly_fields = ['total']


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['id', 'usuario', 'total', 'status_pagamento', 'status_entrega', 'data_criacao']
    list_filter = ['status_pagamento', 'status_entrega', 'data_criacao']
    search_fields = ['usuario__username', 'usuario__email']


@admin.register(EnderecoEntrega)
class EnderecoEntregaAdmin(admin.ModelAdmin):
    list_display = ['id', 'usuario', 'cidade', 'estado', 'principal']
    list_filter = ['estado', 'principal']
    search_fields = ['usuario__username', 'cidade', 'bairro', 'rua']


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'telefone', 'cpf']
    search_fields = ['usuario__username', 'usuario__email', 'cpf', 'telefone']
