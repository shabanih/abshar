from user_app.models import MyHouse


class SubdomainMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        host = request.get_host().split(':')[0]  # بدون پورت
        parts = host.split('.')

        request.subdomain = None
        request.house = None

        if len(parts) >= 2:  # حالا >=2 برای لوکال هم جواب میده
            subdomain = parts[0]

            if subdomain != "www":
                request.subdomain = subdomain
                try:
                    house = MyHouse.objects.get(
                        subdomain=subdomain,
                        is_active=True
                    )
                    request.house = house
                except MyHouse.DoesNotExist:
                    request.house = None

        response = self.get_response(request)
        return response