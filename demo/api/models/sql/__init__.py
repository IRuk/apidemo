import warnings

import reprlib as _repr

from sqlalchemy import inspect
from sqlalchemy.ext.declarative import declarative_base

warnings.filterwarnings('error', module='^pymysql\.')


class _AlchemyRepr(_repr.Repr):
    def repr_AttributeState(self, obj, level):
        return self.repr1(obj.value, level - 1)


_alchemyrepr = _AlchemyRepr()


class _Base(object):

    def to_dict(self):
        columns = inspect(self.__class__).columns.items()
        keys = [column[0] for column in columns]
        instance_state = inspect(self)

        return {key: getattr(self, key) for key in keys
                if key not in instance_state.unloaded}


Base = declarative_base(cls=_Base)
