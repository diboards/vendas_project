# vendas/templatetags/variacao_filters.py
from django import template

register = template.Library()

@register.filter
def get_variacao(variacoes, cor):
    """Filtra as variações por cor"""
    if not variacoes:
        return []
    return [v for v in variacoes if v.cor == cor]

@register.filter
def get_tamanho(variacoes, tamanho):
    """Filtra as variações por tamanho"""
    if not variacoes:
        return None
    for v in variacoes:
        if v.tamanho == tamanho:
            return v
    return None

@register.filter
def first_cor(variacoes, cor):
    """Retorna a primeira variação de uma cor"""
    if not variacoes:
        return None
    for v in variacoes:
        if v.cor == cor:
            return v
    return None
