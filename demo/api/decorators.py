from pyramid.path import DottedNameResolver


def multiple(*decorators):
    def wrapped(f):
        resolver = DottedNameResolver()
        for decorator in decorators:
            f = resolver.maybe_resolve(decorator)(f)
        return f
    return wrapped


def pretty(f):
    def wrapped(context, request):
        if 'pretty' in request.GET and 'application/json' in request.accept:
            request.override_renderer = 'prettyjson'
        return f(context, request)
    return wrapped


def cornice_deserializer(f, deserializer):
    def wrapped(context, request):
        request.deserializer = deserializer
        return f(context, request)
    return wrapped
