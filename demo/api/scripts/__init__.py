import configparser

from zope.sqlalchemy import register
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from demo.api.models.sql import Base
from demo.api.common.utils.settings import sqlalchemy_engine_from_config


def get_settings(ini_file, section='app:main'):
    if isinstance(ini_file, str):
        ini_file = open(ini_file, 'r')

    config = configparser.RawConfigParser()
    config.optionxform = str

    try:
        config.readfp(ini_file)
    except KeyError:
        config.add_section(section)

    return dict(config.items(section))


def init_sqlalchemy(settings, session=None, **kwargs):
    if not session:
        session = scoped_session(sessionmaker())
        register(session)

    engine = sqlalchemy_engine_from_config(settings, **kwargs)
    session.configure(bind=engine)
    Base.metadata.bind = engine

    return session
