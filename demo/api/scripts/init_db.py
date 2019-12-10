"""Initialise database.

Usage: initialisedb INI_FILE [--drop | --drop-tables | --drop-database]


Options:
    -h --help               Show this screen
    --drop                  Alias for --drop-tables
    --drop-tables           Drop all tables (that have a model) before
                            recreating
    --drop-database         Drop the database (if it exists) before creating
                            tables (a new database with the same name is also
                            created)


The user connecting to the database (defined in the ini file) must have
appropriate permissions to either drop tables on the used database.
"""
import logging
import importlib
import pkgutil
import sys
import urllib.parse

from docopt import docopt
import sqlalchemy

from . import get_settings
from . import init_sqlalchemy
from demo.api.models import sql
from demo.api.models.sql import Base


logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)


def load_modules(root_module_name):
    modules = []
    for _, module_name, is_package in pkgutil.iter_modules(
            sys.modules[root_module_name].__path__):

        if is_package:
            continue

        modules.append(importlib.import_module(
            root_module_name + '.' + module_name))

    return modules


def drop_database(settings):
    url = urllib.parse.urlsplit(settings['sqlalchemy.url'])
    db = url.path[1:]  # get rid of the slash
    url = urllib.parse.urlunsplit((url.scheme, url.netloc, '/', url.query,
                                   url.fragment))
    engine = sqlalchemy.create_engine(url)
    conn = engine.connect()
    conn.execute('drop database if exists {} '.format(db))
    conn.execute('create database {}'.format(db))
    conn.close()


def main():
    args = docopt(__doc__)

    ini_file = args['INI_FILE']
    settings = get_settings(ini_file)

    load_modules(sql.__name__)

    # Required to build database
    session = init_sqlalchemy(settings)  # noqa

    if args['--drop'] or args['--drop-tables']:
        Base.metadata.drop_all()
    if args['--drop-database']:
        drop_database(settings)

    Base.metadata.create_all()

    _logger.info('Done.')


if __name__ == "__main__":
    main()
