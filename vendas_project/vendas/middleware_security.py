# vendas/middleware_security.py
from django.http import JsonResponse
import re

class SecurityHeadersMiddleware:
    """Adiciona cabeçalhos de segurança para proteger o navegador do cliente"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # ========================================================== #
        # CABEÇALHOS DE SEGURANÇA                                     #
        # ========================================================== #
        
        # 🔥 Previne MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # 🔥 Previne clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # 🔥 Proteção contra XSS
        response['X-XSS-Protection'] = '1; mode=block'
        
        # 🔥 Controla informações de referência
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # 🔥 Content Security Policy (CSP)
        response['Content-Security-Policy'] = self._get_csp_policy()
        
        # 🔥 Remove cabeçalhos que podem expor informações do servidor
        if 'Server' in response:
            del response['Server']
        if 'X-Powered-By' in response:
            del response['X-Powered-By']
        
        return response
    
    def _get_csp_policy(self):
        """Retorna a política de segurança de conteúdo"""
        return (
            "default-src 'self'; "
            "script-src 'self' https://sdk.mercadopago.com https://cdn.jsdelivr.net https://code.jquery.com 'unsafe-inline'; "
            "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com 'unsafe-inline'; "
            "img-src 'self' data: https://res.cloudinary.com https://*.onrender.com https://*.cloudinary.com; "
            "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
            "connect-src 'self' https://api.mercadopago.com https://*.mercadopago.com; "
            "frame-src 'self' https://www.mercadopago.com.br; "
            "media-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
        )


class BlockSuspiciousRequestsMiddleware:
    """Bloqueia requisições suspeitas (bots tentando acessar arquivos PHP/WordPress)"""
    
    SUSPICIOUS_PATTERNS = [
        r'\.php$',
        r'wp-',
        r'xmlrpc',
        r'\.env',
        r'config\.',
        r'\.sql',
        r'\.bak',
        r'\.old',
        r'\.log',
        r'\.tmp',
        r'\.swp',
        r'\.save',
        r'\.orig',
        r'\.sample',
        r'\.example',
        r'wp-admin',
        r'wp-content',
        r'wp-includes',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.SUSPICIOUS_PATTERNS]
    
    def __call__(self, request):
        path = request.path
        
        # 🔥 Verifica se o caminho é suspeito
        for pattern in self.compiled_patterns:
            if pattern.search(path):
                # Retorna 403 Forbidden para requisições suspeitas
                return JsonResponse({
                    'error': 'Acesso negado',
                    'message': 'Requisição bloqueada por motivos de segurança'
                }, status=403)
        
        return self.get_response(request)
