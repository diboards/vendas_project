# vendas/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Produto, ProdutoVariacao, Venda, EnderecoEntrega, Perfil


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['nome', 'descricao', 'categoria', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProdutoVariacaoForm(forms.ModelForm):
    class Meta:
        model = ProdutoVariacao
        fields = ['cor', 'tamanho', 'preco', 'quantidade_estoque', 'imagem']
        widgets = {
            'cor': forms.Select(attrs={'class': 'form-control'}),
            'tamanho': forms.Select(attrs={'class': 'form-control'}),
            'preco': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'quantidade_estoque': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'imagem': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


class ProdutoVariacaoInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        combinacoes = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                cor = form.cleaned_data.get('cor')
                tamanho = form.cleaned_data.get('tamanho')
                if cor and tamanho:
                    combinacao = f"{cor}_{tamanho}"
                    if combinacao in combinacoes:
                        raise forms.ValidationError(f"Combinação {cor}/{tamanho} já foi adicionada.")
                    combinacoes.append(combinacao)


class VendaForm(forms.ModelForm):
    class Meta:
        model = Venda
        fields = ['produto', 'quantidade', 'observacoes', 'status']


class UsuarioComEnderecoForm(forms.Form):
    nome = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    cpf = forms.CharField(max_length=14, required=True)
    celular = forms.CharField(max_length=15, required=True)
    password1 = forms.CharField(widget=forms.PasswordInput, min_length=6, required=True)
    password2 = forms.CharField(widget=forms.PasswordInput, min_length=6, required=True)
    cep = forms.CharField(max_length=9, required=True)
    rua = forms.CharField(max_length=100, required=True)
    numero = forms.CharField(max_length=10, required=True)
    complemento = forms.CharField(max_length=50, required=False)
    bairro = forms.CharField(max_length=50, required=True)
    cidade = forms.CharField(max_length=50, required=True)
    estado = forms.CharField(max_length=2, required=True)
    principal = forms.BooleanField(required=False, initial=True)


class EnderecoEntregaForm(forms.ModelForm):
    class Meta:
        model = EnderecoEntrega
        fields = ['rua', 'numero', 'complemento', 'bairro', 'cidade', 'estado', 'cep', 'principal']


# 🔥 ADICIONAR ESTA CLASSE
class PerfilForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False, label="Nome")
    last_name = forms.CharField(max_length=30, required=False, label="Sobrenome")
    email = forms.EmailField(required=True, label="E-mail")
    
    class Meta:
        model = Perfil
        fields = ['telefone', 'cpf', 'data_nascimento', 'bio']
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'usuario') and self.instance.usuario:
            self.fields['first_name'].initial = self.instance.usuario.first_name
            self.fields['last_name'].initial = self.instance.usuario.last_name
            self.fields['email'].initial = self.instance.usuario.email
    
    def save(self, commit=True):
        perfil = super().save(commit=False)
        if commit:
            perfil.save()
            usuario = perfil.usuario
            usuario.first_name = self.cleaned_data.get('first_name', '')
            usuario.last_name = self.cleaned_data.get('last_name', '')
            usuario.email = self.cleaned_data.get('email', '')
            usuario.save()
        return perfil

# vendas/forms.py

class OrcamentoForm(forms.Form):
    AMBIENTE_CHOICES = [
        ('', 'Escolha uma opção'),
        ('sala', 'Sala de Estar'),
        ('quarto', 'Quarto'),
        ('cozinha', 'Cozinha'),
        ('banheiro', 'Banheiro'),
        ('escritorio', 'Escritório'),
        ('outro', 'Outro'),
    ]
    ORCAMENTO_CHOICES = [
        ('', 'Escolha uma opção'),
        ('5-10', 'R$ 5.000 - R$ 10.000'),
        ('10-20', 'R$ 10.000 - R$ 20.000'),
        ('20-50', 'R$ 20.000 - R$ 50.000'),
        ('50+', 'Acima de R$ 50.000'),
    ]

    nome = forms.CharField(
        label='Seu nome',
        required=True,
        error_messages={'required': 'Insira seu nome.'}
    )
    telefone = forms.CharField(
        label='DDD + Whatsapp',
        max_length=15,
        required=True,
        error_messages={'required': 'Insira o número de WhatsApp.'}
    )
    ambiente = forms.ChoiceField(
        choices=AMBIENTE_CHOICES,
        required=True,
        error_messages={'required': 'Escolha um ambiente.'}
    )
    orcamento = forms.ChoiceField(
        choices=ORCAMENTO_CHOICES,
        required=True,
        error_messages={'required': 'Escolha um orçamento.'}
    )

    def clean_ambiente(self):
        data = self.cleaned_data.get('ambiente')
        if data == '':
            raise forms.ValidationError('Escolha um ambiente.')
        return data

    def clean_orcamento(self):
        data = self.cleaned_data.get('orcamento')
        if data == '':
            raise forms.ValidationError('Escolha um orçamento.')
        return data
