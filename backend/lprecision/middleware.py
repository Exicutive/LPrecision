class PrivateApiCacheControlMiddleware:
    """Keep authenticated API responses out of browser and proxy caches."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-store, max-age=0, private'
            response['Pragma'] = 'no-cache'
        return response
