from distutils.version import Version
import logging
import pkg_resources
import sys

from pyramid.httpexceptions import HTTPException
from pyramid.httpexceptions import HTTPInternalServerError

from ._averages import *  # noqa
from ..sql import Session
from demo.api.models.sql.readings import all_tables

_logger = logging.getLogger(__name__)


def error(context, request):
    """Return a JSON formatted error response.

    The main purpose of this is to format the error response in a way that is
    understood by the client (based on the Accept header). The HTTP exception
    classes already handle text/html and text/plain. This view adds support
    for application/json.

    This view should be configured with a JSON renderer.
    """
    if not isinstance(context, HTTPException):
        response = HTTPInternalServerError()

        if (sys.exc_info() != (None, None, None)):
            _logger.exception('Unhandled exception')
    else:
        response = context

    if request.application != 'api':
        best_match = request.accept.best_match(
            ('text/html', 'text/plain', 'application/json'))
        if best_match != 'application/json':
            return response

    if response.content_type == 'application/json':
        return response
    request.response.status = response.status
    body = {'status': response.title.lower()}
    if response.detail:
        body['description'] = response.detail.lower()
    return body


def _table_counts():
    counts = []
    for table in all_tables.values():
        table_name = table.__table__.name
        row_count = Session.query(table).count()
        counts.append((table_name, row_count))
    return counts


def demo_home(request):
    """Get demo main page data."""
    dist = __name__.split('.')
    dist = '-'.join(dist[:2])

    if isinstance(dist, str):
        version = pkg_resources.get_distribution(dist).version
    elif isinstance(dist, pkg_resources.Distribution):
        version = dist.version
    elif isinstance(dist, Version):
        version = str(dist)
    else:
        raise ValueError('Invalid dist value')

    return {'version': version,
            'database_row_counts': _table_counts()}
