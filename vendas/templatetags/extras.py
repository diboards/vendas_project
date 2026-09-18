# vendas/templatetags/extras.py
from django import template
import json

register = template.Library()

@register.filter
def pluck(queryset, key):
    return json.dumps([q[key] for q in queryset])


@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})

# templatetags/extras.py
from django import template

register = template.Library()

@register.filter
def get_imagem_url(item):
    if item.imagem_selecionada:
        return item.imagem_selecionada.url
    elif item.produto.imagem:
        return item.produto.imagem.url
    return '/static/vendas/images/default-product.png'