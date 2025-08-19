from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Simple health check endpoint for Railway"""
    return JsonResponse({
        'status': 'healthy',
        'message': 'Django app is running',
        'timestamp': '2025-08-19'
    }, status=200)
