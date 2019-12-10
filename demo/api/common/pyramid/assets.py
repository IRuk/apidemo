"""Assets mapping for Pyramid apps.

Include the module in Pyramid:

    config.include('demo.api.common.pyramid.assets')

Add an assets mapping, e.g.:

    config.add_assets_mapping(
        {'demo.api:static/foo.css': 'demo.api:static/foo.98da6783.css'})

`request.static_url('demo.api:static/foo.css')` outputs the mangled URL, e.g.:

    http://127.0.0.1:8080/static/foo.98da6783.css

`request.static_path` works the same way (calls `request.static_url`).
"""
from functools import partial

from pyramid.events import NewRequest
from zope.interface import implementer
from zope.interface import Interface


class IAssets(Interface):
    pass


@implementer(IAssets)
class Assets(dict):
    pass


def static_url(func, request, path, **kw):
    assets = request.registry.queryUtility(IAssets, default={})
    return func(assets.get(path, path), **kw)


def wrap_request(event):
    request = event.request
    request.static_url = partial(static_url, request.static_url, request)


def add_assets_mapping(config, mapping):
    """Register an assets mapping.

    This functions should be called with a mapping in the form of:

    {'demo.api:static/foo.css': 'demo.api:static/foo.98da6783.css'}
    """
    assets = config.registry.queryUtility(IAssets) or Assets()
    assets.update(mapping)
    config.registry.registerUtility(assets, IAssets)


def includeme(config):
    config.add_directive('add_assets_mapping', add_assets_mapping)
    config.add_subscriber(wrap_request, NewRequest)
    config.registry.registerUtility(Assets(), IAssets)
