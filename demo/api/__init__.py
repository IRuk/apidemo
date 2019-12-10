import json

import pkg_resources
from cornice import Service
from pyramid.config import Configurator
from pyramid.interfaces import IExceptionResponse
from pyramid.path import DottedNameResolver
from pyramid.settings import asbool

from .decorators import multiple
from .deserializers import extract_json_data_factory
from .renderers import compact_json_renderer
from .renderers import compact_jsonp_renderer
from .renderers import pretty_json_renderer
from .sql import Base
from .sql import Session
from demo.api.common.utils.settings import sqlalchemy_engine_from_config


def main(global_config, **settings):
    # settings may be defined in the global configuration
    settings = dict(
        [(key, value) for key, value in global_config.items()
         if key not in ('__file__', 'here')],
        **settings)

    engine = sqlalchemy_engine_from_config(settings)
    Session.configure(bind=engine)
    Base.metadata.bind = engine

    # XXX: Basic authentication and authorization omitted purposefully,
    # unneeded
    config = Configurator(settings=settings,
                          authentication_policy=None,
                          authorization_policy=None)

    # Disable Cornice's built-in exception handling
    config.add_settings(handle_exceptions=False)
    config.include('cornice')
    config.include('pyramid_jinja2')
    config.include('pyramid_tm')
    config.include('demo.api.common.pyramid.assets')
    config.include(add_routes)
    config.include(add_views)
    config.include(add_request_methods)
    config.include(add_jinja2)
    config.include(add_renderers)

    config.add_assets_mapping(json.load(
        pkg_resources.resource_stream(__name__, 'static/assets.json')))

    config.add_cornice_deserializer('application/json',
                                    extract_json_data_factory())
    config.add_cornice_deserializer('application/json-patch+json',
                                    extract_json_data_factory())

    for service in create_cornice_services(path_prefix='/api'):
        config.add_cornice_service(service)

    return config.make_wsgi_app()


def add_renderers(config):
    config.add_renderer('json', compact_json_renderer)
    config.add_renderer('prettyjson', pretty_json_renderer)
    config.add_renderer('jsonp', compact_jsonp_renderer)
    config.add_renderer('.html', 'pyramid_jinja2.renderer_factory')
    config.add_renderer('.txt', 'pyramid_jinja2.renderer_factory')


def add_routes(config):
    config.add_route('demo_home', '/')
    config.add_route('demo_average', '/demo_average')

    if asbool(config.get_settings().get('proxy.enabled', False)):
        config.add_route('proxy', config.get_settings()['proxy.pattern'])


def add_views(config, proxy_enabled=False):
    config.add_view('.views.error', context=IExceptionResponse,
                    decorator=multiple('.decorators.pretty',),
                    renderer='json')
    config.add_view('.views.error', context=Exception,
                    decorator=multiple('.decorators.pretty',),
                    renderer='json')

    config.add_view('.views.demo_home', route_name='demo_home',
                    renderer='home.html')

    config.add_view('.views.demo_average', route_name='demo_average',
                    renderer='average.html')

    static_prefix = config.get_settings().get('static.prefix', '')

    config.add_static_view(static_prefix, 'static/dist/', cache_max_age=0)

    if asbool(config.get_settings().get('proxy.enabled', False)):
        config.add_view('.views.proxy', route_name='proxy')


def add_request_methods(config):
    class _Placeholder(object):
        def __init__(self, value):
            self.value = value

        def __get__(self, instance, owner):
            return self.value

        def __set__(self, instance, value):
            self.value = value

    # Override the default webob.Request.json property to make it reified
    config.add_request_method(lambda request: request.json_body, 'json',
                              reify=True)
    config.add_request_method(lambda request: 'api', 'application', reify=True)


def add_jinja2(config):
    config.add_jinja2_search_path('demo.api:templates/')


def create_cornice_services(path_prefix=''):
    path = lambda original_path: path_prefix + original_path  # noqa
    resolver = DottedNameResolver()
    Service.default_filters = []

    # /average

    average = Service('average', path('/average'), renderer='json')

    average.add_view(
        'get', resolver.resolve('.views.get_averages'),
        accept='application/json',
        decorator=multiple('.decorators.pretty',),
        schema=resolver.resolve('.schemas.AverageQuerySchema'),
        permission=None,
        renderer='jsonp')

    return [
        average
    ]
