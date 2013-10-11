
class FurconURLSMiddleware(object):

    def process_request(self, request):
        if request.path.startswith('/furcon/'):
            request.urlconf = 'furcon.urls'
