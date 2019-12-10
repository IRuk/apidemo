from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Float
from sqlalchemy import String
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr

from . import Base
from .postcode import PostcodeArea
from .postcode import PostcodeUnit
from .postcode import PostcodeDistrict


class ReadingMixin(object):
    """A reading mixin.

    Attributes:
    id -- An id for the reading entry
    download -- Download percentage
    upload -- Upload percentage
    year -- Year for the reading
    postcode_area_id -- The postcode area id
    postcode_district_id -- The postcode district
    postcode_sector -- The postcode sector. It is made up of a single digit
    postcode_unit_id -- The postcode unit id

    """
    __table_args__ = (
        {'mysql_charset': 'UTF8MB4', 'mysql_engine': 'InnoDB'},
    )

    @declared_attr
    def id(cls):
        return Column(Integer, primary_key=True)

    @declared_attr
    def postcode_sector(cls):
        return Column(String(1), nullable=False)

    @declared_attr
    def download(cls):
        return Column(Float, nullable=True)

    @declared_attr
    def upload(cls):
        return Column(Float, nullable=True)

    @declared_attr
    def year(cls):
        return Column(Integer, nullable=False)

    @declared_attr
    def postcode_area_id(cls):
        return Column(Integer, ForeignKey(PostcodeArea.id), nullable=False)

    @declared_attr
    def postcode_district_id(cls):
        return Column(Integer, ForeignKey(PostcodeDistrict.id), nullable=False)

    @declared_attr
    def postcode_unit_id(cls):
        return Column(Integer, ForeignKey(PostcodeUnit.id), nullable=False)

    @declared_attr
    def postcode_area(cls):
        return relationship(
            PostcodeArea, lazy='joined', innerjoin=True,
            backref=backref(cls.reading_type + '_reading_postcodes_areas',
                            lazy='dynamic'))

    @declared_attr
    def postcode_district(cls):
        return relationship(
            PostcodeDistrict, lazy='joined', innerjoin=True,
            backref=backref((cls.reading_type +
                             '_reading_postcodes_districts'),
                            lazy='dynamic'))

    @declared_attr
    def postcode_unit(cls):
        return relationship(
            PostcodeUnit, lazy='joined', innerjoin=True,
            backref=backref(cls.reading_type + '_reading_postcodes_units',
                            lazy='dynamic'))


class Reading(Base, ReadingMixin):
    """An average reading."""

    __tablename__ = 'average_readings'
    reading_type = 'average'


class ReadingSlow(Base, ReadingMixin):
    """A reading for slow lines at less than 10Mbit."""

    __tablename__ = 'slow_readings'
    reading_type = 'slow'


class ReadingBB(Base, ReadingMixin):
    """A reading for BB lines."""

    __tablename__ = 'BB_readings'
    reading_type = 'BB'


class ReadingSFBB(Base, ReadingMixin):
    """A reading for SFBB lines."""

    __tablename__ = 'SFBB_readings'
    reading_type = 'SFBB'


class ReadingUFBB(Base, ReadingMixin):
    """A reading for UFBB lines."""

    __tablename__ = 'UFBB_readings'
    reading_type = 'UFBB'


all_tables = {
    '0': Reading,
    '1': ReadingSlow,
    '2': ReadingBB,
    '3': ReadingSFBB,
    '4': ReadingUFBB}
