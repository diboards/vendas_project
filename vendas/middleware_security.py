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
            # Scripts permitidos (Mercado Pago SDK, Bootstrap, jQuery)
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
                "https://sdk.mercadopago.com "
                "https://*.mercadopago.com "
                "https://*.mercadolibre.com "
                "https://cdn.jsdelivr.net "
                "https://code.jquery.com; "
            # Estilos (Bootstrap, Google Fonts)
            "style-src 'self' 'unsafe-inline' "
                "https://cdn.jsdelivr.net "
                "https://fonts.googleapis.com "
                "https://*.mercadopago.com "
                "https://*.mercadolibre.com; "
            # Imagens (Cloudinary + Mercado Pago fingerprint/tracking)
            "img-src 'self' data: blob: "
                "https://res.cloudinary.com "
                "https://*.onrender.com "
                "https://*.cloudinary.com "
                "https://www.mercadolibre.com "
                "https://*.mercadolibre.com "
                "https://www.mercadolivre.com "
                "https://*.mercadopago.com; "
            # Fontes
            "font-src 'self' data: "
                "https://cdn.jsdelivr.net "
                "https://fonts.gstatic.com; "
            # Conexões (fetch, XHR) - Mercado Pago precisa do mercadolibre.com
            "connect-src 'self' "
                "https://api.mercadopago.com "
                "https://*.mercadopago.com "
                "https://api.mercadolibre.com "
                "https://*.mercadolibre.com "
                "https://www.mercadolibre.com; "
            # Iframes (checkout do Mercado Pago)
            "frame-src 'self' "
                "https://www.mercadopago.com.br "
                "https://*.mercadopago.com "
                "https://www.mercadolibre.com "
                "https://*.mercadolibre.com; "
            # Vídeos/áudio
            "media-src 'self'; "
            # Bloqueios
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
