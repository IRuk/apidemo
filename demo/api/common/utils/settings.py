from __future__ import absolute_import

import pkg_resources
import sqlalchemy


def sqlalchemy_engine_from_config(configuration, prefix='sqlalchemy.',
                                  **kwargs):
    """Set up a SQLAlchemy engine.

    This sets up an SQLalchemy engine and configures any registered converters.
    Converters can be registered using the entry-point group:
    `demo.api.pymysql` and the name `conversions`. The entry point should
    contain a dict with a mapping from types to conversion functions which
    will be used to update the default converters. The used converter
    if multiple converters are registered for the same type is undefined.
    """
    assert 'connect_args' not in kwargs

    url = sqlalchemy.engine.url.make_url(configuration[prefix + 'url'])
    if url.drivername == 'mysql+pymysql':
        import pymysql
        conversions = pymysql.converters.conversions.copy()

        for entry_point in pkg_resources.iter_entry_points(
                'demo.api.pymysql', 'conversions'):
            conversions.update(entry_point.load())
        kwargs['connect_args'] = {'conv': conversions}

    return sqlalchemy.engine_from_config(
        configuration, prefix, **kwargs)
