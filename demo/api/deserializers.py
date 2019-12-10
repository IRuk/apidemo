import simplejson


def extract_json_data_factory(**kwargs):
    def extract_json_data(request):
        if request.body:
            try:
                return simplejson.loads(request.body, **kwargs)
            except ValueError as error:
                request.errors.add(
                    'body', None,
                    'Invalid JSON request body: {}'.format(error))
        return {}
    return extract_json_data
