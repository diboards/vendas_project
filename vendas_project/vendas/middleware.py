# vendas/middleware.py
from django.core.cache import cache
from django.conf import settings

class DynamicCacheMiddleware:
    """Middleware para cachear páginas dinamicamente"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_urls = getattr(settings, 'CACHE_EXCLUDED_URLS', [])
    
    def __call__(self, request):
        path = request.path
        
        # 🔥 VERIFICA SE O USUÁRIO ESTÁ AUTENTICADO (com tratamento de erro)
        try:
            is_authenticated = request.user.is_authenticated
        except AttributeError:
            # Se não tiver user, não usa cache
            return self.get_response(request)
        
        # Se for uma URL excluída, não usa cache
        for excluded in self.excluded_urls:
            if path.startswith(excluded):
                return self.get_response(request)
        
        # Se não for GET, não usa cache
        if request.method != 'GET':
            return self.get_response(request)
        
        # Se o usuário está logado, não usa cache
        if is_authenticated:
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
            cache.set(cache_key, response, 300)
        
        return response
