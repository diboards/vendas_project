# vendas/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.auth.models import BaseUserManager
from decimal import Decimal
from cloudinary.models import CloudinaryField
from django.core.validators import RegexValidator

# ============================================
# CONSTANTES - DEFINIDAS PRIMEIRO
# ============================================

CATEGORIA_CHOICES = [
    ('lancamentos', 'Lançamentos'),
    ('promocoes', 'Promoções'),
    ('conjuntos', 'Conjuntos'),
    ('destaque', 'Destaque'),  # 🔥 NOVA OPÇÃO
    ('outros', 'Outros'),
]

TAMANHO_CHOICES = [
    ('PP', 'PP'),
    ('P', 'P'),
    ('M', 'M'),
    ('G', 'G'),
    ('GG', 'GG'),
    ('U', 'Único'),
]

COR_CHOICES = [
    ('Vermelho', 'Vermelho'),
    ('Azul', 'Azul'),
    ('Verde', 'Verde'),
    ('Amarelo', 'Amarelo'),
    ('Preto', 'Preto'),
    ('Branco', 'Branco'),
    ('Rosa', 'Rosa'),
    ('Roxo', 'Roxo'),
    ('Laranja', 'Laranja'),
    ('Cinza', 'Cinza'),
    ('Marrom', 'Marrom'),
    ('Outro', 'Outro'),
]

# ============================================
# MODELOS
# ============================================

class Produto(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='outros')
    imagem = CloudinaryField('imagem', blank=True, null=True)
    ativo = models.BooleanField(default=True)
    data_cadastro = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['nome']
    
    def __str__(self):
        return self.nome


class ProdutoVariacao(models.Model):
    """Variação do produto (ex: Conjunto - Azul - M)"""
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='variacoes')
    cor = models.CharField(max_length=20, choices=COR_CHOICES)
    tamanho = models.CharField(max_length=10, choices=TAMANHO_CHOICES)
    preco = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    quantidade_estoque = models.PositiveIntegerField(default=0)
    imagem = CloudinaryField('imagem', blank=True, null=True)
    
    class Meta:
        unique_together = ['produto', 'cor', 'tamanho']
        ordering = ['cor', 'tamanho']
    
    def __str__(self):
        return f"{self.produto.nome} - {self.cor}/{self.tamanho}"


class CarrinhoItem(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    # 🔥 ADICIONAR null=True, blank=True
    variacao = models.ForeignKey(ProdutoVariacao, on_delete=models.CASCADE, null=True, blank=True)
    quantidade = models.PositiveIntegerField(default=1)
    data_adicionado = models.DateTimeField(auto_now_add=True)
    
    @property
    def subtotal(self):
        if self.variacao:
            return self.variacao.preco * self.quantidade
        return 0
    
    def __str__(self):
        if self.variacao:
            return f"{self.variacao.produto.nome} - {self.usuario.username}"
        return f"Carrinho - {self.usuario.username}"


class ItemPedido(models.Model):
    pedido = models.ForeignKey('Pedido', on_delete=models.CASCADE, related_name='itens_pedido')
    variacao = models.ForeignKey(ProdutoVariacao, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def subtotal(self):
        return self.preco_unitario * self.quantidade
    
    def __str__(self):
        return f"{self.variacao.produto.nome} - Pedido #{self.pedido.id}"


class EnderecoEntrega(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enderecos")
    cep = models.CharField(max_length=9)
    rua = models.CharField(max_length=100)
    numero = models.CharField(max_length=10)
    complemento = models.CharField(max_length=50, blank=True)
    bairro = models.CharField(max_length=50)
    cidade = models.CharField(max_length=50)
    estado = models.CharField(max_length=2)
    principal = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.principal:
            EnderecoEntrega.objects.filter(
                usuario=self.usuario, 
                principal=True
            ).exclude(id=self.id).update(principal=False)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.rua}, {self.numero} - {self.bairro}, {self.cidade}/{self.estado}"
    
    class Meta:
        verbose_name_plural = "Endereços de Entrega"


class Pedido(models.Model):
    METODO_PAGAMENTO_CHOICES = [
        ('pix', 'PIX'),
        ('cartao', 'Cartão de Crédito'),
    ]

    TIPO_ENTREGA_CHOICES = [
        ('retirada', 'Retirada na Loja'),
        ('entrega', 'Entrega'),
    ]

    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aguardando_aprovacao', 'Aguardando Aprovação'),
        ('aprovado', 'Aprovado'),
        ('processando', 'Processando'),
        ('enviado', 'Enviado'),
        ('entregue', 'Entregue'),
        ('cancelado', 'Cancelado'),
    ]

    STATUS_PAGAMENTO_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]

    STATUS_ENTREGA_CHOICES = [
        ('aguardando', 'Aguardando'),
        ('preparando', 'Preparando'),
        ('enviado', 'Enviado'),
        ('entregue', 'Entregue'),
        ('retirado', 'Retirado'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_criacao = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    status_pagamento = models.CharField(max_length=20, choices=STATUS_PAGAMENTO_CHOICES, default='pendente')
    status_entrega = models.CharField(max_length=20, choices=STATUS_ENTREGA_CHOICES, default='aguardando')

    endereco_entrega = models.ForeignKey('EnderecoEntrega', on_delete=models.SET_NULL, null=True, blank=True)
    metodo_pagamento = models.CharField(max_length=20, choices=METODO_PAGAMENTO_CHOICES, default='pix')
    tipo_entrega = models.CharField(max_length=20, choices=TIPO_ENTREGA_CHOICES, default='retirada')
    frete = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    id_mercado_pago = models.CharField(max_length=100, blank=True, null=True)
    qr_code = models.TextField(blank=True, null=True)
    qr_code_base64 = models.TextField(blank=True, null=True)
    numero_cartao = models.CharField(max_length=4, blank=True, null=True)
    validade_cartao = models.CharField(max_length=5, blank=True, null=True)
    nome_cartao = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.username}"

    class Meta:
        ordering = ['-data_criacao']

#Nova venda A ser implementada!
class Venda(models.Model):
    STATUS_CHOICES = [
        ('concluida', 'Concluída'),
        ('pendente', 'Pendente'),
        ('cancelada', 'Cancelada'),
    ]
    
    vendedor = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # 🔥 ADICIONE
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    variacao = models.ForeignKey(ProdutoVariacao, on_delete=models.CASCADE, null=True, blank=True)
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='concluida')
    observacoes = models.TextField(blank=True, null=True)
   
    data_criacao = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    
    @property
    def total(self):
        return self.quantidade * self.preco_unitario
    
    def __str__(self):
        return f"Venda #{self.id} - {self.produto.nome}"


class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    telefone = models.CharField(
        max_length=15, 
        blank=True, 
        null=True,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Número de telefone inválido")]
    )
    cpf = models.CharField(max_length=14, blank=True, null=True, verbose_name="CPF")
    data_nascimento = models.DateField(blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfis"

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


class EmailUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)
