from sqlalchemy.ext import baked
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from zope.sqlalchemy import register

from demo.api.models.sql import Base  # noqa

Session = scoped_session(sessionmaker())
register(Session)

bakery = baked.bakery()
