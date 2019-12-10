import logging

from pyramid.httpexceptions import HTTPBadRequest
from sqlalchemy import desc

from ..schemas import AverageItemsSchema
from ..sql import Session
from demo.api.common.utils.postcodes import get_postcode_areas
from demo.api.common.utils.postcodes import get_postcode_districts
from demo.api.common.utils.postcodes import get_postcode_units
from demo.api.common.utils.postcodes import split_postcode
from demo.api.models.sql.readings import all_tables
from demo.api.common.utils import FRIENDLY_CONNECTION_CATEGORIES

_logger = logging.getLogger(__name__)

POSTCODE_AREAS = {}
POSTCODE_DISTRICTS = {}
POSTCODE_UNITS = {}


def clear_postcode_caching():
    """Clear postcode part caching."""
    POSTCODE_AREAS.clear()
    POSTCODE_DISTRICTS.clear()
    POSTCODE_UNITS.clear()


def _get_averages(categories, postcode_area_id, district_id, sector, unit_id):
    """Get averages from database tables.

        categories: categories for database table selection. Example '0'
        postcode_area_id: postcode area id referencing row entry in table
                          postcode_areas
        district_id: district id referencing row entry in table
                     postcode_districts
        sector: the sector value used to check a row in any results table
        unit_id: unit id referencing row entry in table postcode_units

    Returns:
        Results as key value pairs containing connection, upload average,
        download upload
    """
    tables = [all_tables[catergory] for catergory in categories]

    results = []
    for table in tables:
        entry = (Session.query(table)
                 .filter(table.postcode_area_id == postcode_area_id,
                         table.postcode_district_id == district_id,
                         table.postcode_sector == sector,
                         table.postcode_unit_id == unit_id)
                 .order_by(desc(table.year))
                 .first())

        if entry:
            results.append({'connection': table.reading_type,
                            'upload': entry.upload if entry else None,
                            'download': entry.download if entry else None})

    return results


def get_averages(request):
    """Get average endpoint."""
    postcode = request.validated['postcode']
    connection = request.validated['connection']

    postcode_parts = split_postcode(postcode)

    if postcode_parts is None:
        raise HTTPBadRequest('Invalid postal code')

    area, district, sector, unit = postcode_parts

    if not POSTCODE_AREAS:
        POSTCODE_AREAS.update(dict(get_postcode_areas(Session)))
        POSTCODE_DISTRICTS.update(dict(get_postcode_districts(Session)))
        POSTCODE_UNITS.update(dict(get_postcode_units(Session)))

    postcode_area_id = POSTCODE_AREAS.get(area)
    district_id = POSTCODE_DISTRICTS.get(district)
    unit_id = POSTCODE_UNITS.get(unit)

    results = []
    if (postcode_area_id is not None and district_id is not None and
            unit_id is not None):
        if connection == 'all':
            categories = FRIENDLY_CONNECTION_CATEGORIES.values()
        else:
            try:
                categories = [FRIENDLY_CONNECTION_CATEGORIES[connection]]
            except KeyError:
                raise HTTPBadRequest('Invalid connection type')

        results = _get_averages(
            categories, postcode_area_id, district_id, sector, unit_id)

    return AverageItemsSchema().serialize(results)


def demo_average(request):
    """Get demo average page data."""
    postcode = request.params['postcode']
    connection = request.params['connection'] or 'average'

    postcode_parts = split_postcode(postcode)

    meesage = 'No results.'
    results = []
    if postcode_parts:
        area, district, sector, unit = postcode_parts

        if not POSTCODE_AREAS:
            POSTCODE_AREAS.update(dict(get_postcode_areas(Session)))
            POSTCODE_DISTRICTS.update(dict(get_postcode_districts(Session)))
            POSTCODE_UNITS.update(dict(get_postcode_units(Session)))

        postcode_area_id = POSTCODE_AREAS.get(area)
        district_id = POSTCODE_DISTRICTS.get(district)
        unit_id = POSTCODE_UNITS.get(unit)

        if (postcode_area_id is not None and district_id is not None and
                unit_id is not None):
            categories = []
            if connection == 'all':
                categories = FRIENDLY_CONNECTION_CATEGORIES.values()
            else:
                try:
                    categories = [FRIENDLY_CONNECTION_CATEGORIES[connection]]
                except KeyError:
                    meesage = 'Invalid connection.'

            results = _get_averages(
                categories, postcode_area_id, district_id, sector, unit_id)
    else:
        meesage = 'Invalid postal code.'

    return {'results': results,
            'message': '' if results else meesage}
