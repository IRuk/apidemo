from sqlalchemy import Column
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String

from . import Base


class PostcodeArea(Base):
    """A postcode area.

    Consists of either one or two characters long and is alphabetical.

    Attributes:
    id -- An id
    area -- The postcode area

    """

    __tablename__ = 'postcode_areas'
    __table_args__ = (
        Index('area_idx', 'area', unique=True),
        {'mysql_charset': 'UTF8MB4', 'mysql_engine': 'InnoDB'},
    )

    id = Column(Integer, primary_key=True)
    area = Column(String(2), nullable=False)


class PostcodeDistrict(Base):
    """A postcode district.

    Consists of one digit, two digits or a digit followed by a letter.

    Attributes:
    id -- An id
    district -- The postcode district

    """

    __tablename__ = 'postcode_districts'
    __table_args__ = (
        Index('district_idx', 'district', unique=True),
        {'mysql_charset': 'UTF8MB4', 'mysql_engine': 'InnoDB'},
    )

    id = Column(Integer, primary_key=True)
    district = Column(String(2), nullable=False)


class PostcodeUnit(Base):
    """A postcode unit.

    Consists of two characters added to the end of the postcode sector.

    Attributes:
    id -- An id
    unit -- The postcode unit

    """

    __tablename__ = 'postcode_units'
    __table_args__ = (
        Index('unit_idx', 'unit', unique=True),
        {'mysql_charset': 'UTF8MB4', 'mysql_engine': 'InnoDB'},
    )

    id = Column(Integer, primary_key=True)
    unit = Column(String(3), nullable=False)
