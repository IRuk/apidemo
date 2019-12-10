import re

from demo.api.models.sql.postcode import PostcodeArea
from demo.api.models.sql.postcode import PostcodeUnit
from demo.api.models.sql.postcode import PostcodeDistrict

postcode_regex = re.compile(
    r'^([A-Z]{1,2})([0-9]{1,2}|[0-9][A-Z])\s*([0-9])([A-Z]{2})$')


def get_postcode_areas(session):
    return (session.query(PostcodeArea)
            .with_entities(PostcodeArea.area, PostcodeArea.id)
            .all())


def get_postcode_districts(session):
    return (session.query(PostcodeDistrict)
            .with_entities(PostcodeDistrict.district, PostcodeDistrict.id)
            .all())


def get_postcode_units(session):
    return (session.query(PostcodeUnit)
            .with_entities(PostcodeUnit.unit, PostcodeUnit.id)
            .all())


def split_postcode(postcode):
    postcode = postcode.upper() if postcode else postcode
    parts = postcode_regex.match(postcode)
    return parts.groups() if parts else None
