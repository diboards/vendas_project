# vendas/middleware.py
from django.core.cache import cache
from django.conf import settings
import re

class DynamicCacheMiddleware:
    """Middleware para cachear páginas dinamicamente"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs que NUNCA devem ser cacheadas
        self.excluded_urls = getattr(settings, 'CACHE_EXCLUDED_URLS', [])
    
    def __call__(self, request):
        # Verifica se a URL deve ser cacheadas
        path = request.path
        
        # Se for uma URL excluída, não usa cache
        for excluded in self.excluded_urls:
            if path.startswith(excluded):
                return self.get_response(request)
        
        # Se não for GET, não usa cache
        if request.method != 'GET':
            return self.get_response(request)
        
        # Se o usuário está logado, não usa cache
        if request.user.is_authenticated:
            return self.get_response(request)
        
        # 🔥 Tenta buscar do cache
        cache_key = f'page_cache_{path}_{request.GET.urlencode()}'
        cached_response = cache.get(cache_key)
        
        if cached_response:
            return cached_response
        
        # Se não tiver cache, processa a requisição
        response = self.get_response(request)
        
        # 🔥 Salva no cache
        if response.status_code == 200:
            cache.set(cache_key, response, 300)  # 5 minutos
        
        return response
