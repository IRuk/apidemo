import decimal

from colander import _null
from pyramid.renderers import JSON
from pyramid.renderers import JSONP
import simplejson


def colander_null_adapter(obj, request):
    return None


def immutable_collection_adapter(obj, request):
    return obj._data


def decimal_adapter(obj, request):
    value = str(obj)
    if ('Decimal-As-String' in request.headers or
            'decimal_as_string' in request.params):
        return value
    return simplejson.raw_json.RawJSON(value)


adapters = [
    (_null, colander_null_adapter),
    (decimal.Decimal, decimal_adapter),
]


def _dumps(value, **kwargs):
    # Cornice patches the renderes to use simplejson and sets
    # use_decimal=True always. We handle the decimal encoding
    # so override that here.
    kwargs['use_decimal'] = False
    return simplejson.JSONEncoder(**kwargs).encode(value)


compact_json_renderer = JSON(adapters=adapters, serializer=_dumps,
                             separators=(',', ':'))

compact_jsonp_renderer = JSONP(adapters=adapters, serializer=_dumps,
                               separators=(',', ':'))

pretty_json_renderer = JSON(adapters=adapters, serializer=_dumps,
                            sort_keys=True, indent=2)
