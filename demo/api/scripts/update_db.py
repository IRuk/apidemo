"""Update database.

Usage: updatedb INI_FILE YEAR CSV_FILEPATH
                [--drop | --drop-tables | --drop-database] [--dry-run]
                [--postcode-header POSTCODE_HEADER]...
                [--down-header DHEADER]...
                [--up-header UHEADER]...

Options:
    -h --help                  Show this screen
    -n --dry-run               Do not store anything; useful for showing
                               warnings
    --postcode-header          Postcode header name
    -d --down-header DHEADER   Optional indexed download header name
                               replacement. Defaults to internal names.
                               See indexed headers
                               description and defaults below.
    -u --up-header UHEADER     Optional indexed upload header name replacement.
                               Defaults to internal names. See indexed headers

The user connecting to the database (defined in the ini file) must have
appropriate permissions to either drop tables on the used database.

Indexed headers:
    Header indexes represent the subset for the header type. Index start at 0
    are separated from the header name by a colon.
    Header with index 0 which will use column to populate the 'overall
    average', any subsequent index is used to store subsequent indexes. Care
    must be taken to not swap the header types for the stored samples by index.

    Example 1, '0:Download'
    Example 2, '1:Download < 10Mbit/s'

Default postcode header:
    {0}

Default download header arguments:
{1}

Default upload header arguments:
{2}
"""
import os
import logging
import glob
import csv
import datetime
import itertools

from docopt import docopt
import transaction

from . import init_sqlalchemy
from . import get_settings
from demo.api.common.utils.postcodes import get_postcode_areas
from demo.api.common.utils.postcodes import get_postcode_districts
from demo.api.common.utils.postcodes import get_postcode_units
from demo.api.common.utils.postcodes import split_postcode
from demo.api.models.sql.postcode import PostcodeArea
from demo.api.models.sql.postcode import PostcodeUnit
from demo.api.models.sql.postcode import PostcodeDistrict
from demo.api.models.sql.readings import all_tables


logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)


POSTCODE_CSV_HEADER = 'postcode'
DEFAULT_DOWNLOAD_CSV_HEADERS = [
    '0:Average download speed (Mbit/s)',
    '1:Average download speed (Mbit/s) for lines  < 10Mbit/s',
    '2:Average download speed (Mbit/s) for Basic BB lines',
    '3:Average download speed (Mbit/s) for SFBB lines',
    '4:Average download speed (Mbit/s) for UFBB lines']
DEFAULT_UPLOAD_CSV_HEADERS = [
    '0:Average upload speed (Mbit/s)',
    '1:Average upload speed (Mbit/s) for lines <10Mbit/s',
    '2:Average upload speed (Mbit/s) for Basic BB lines',
    '3:Average upload speed (Mbit/s) for SFBB lines',
    '4:Average upload speed (Mbit/s) for UFBB lines']


def replace_header_arg(storage, header_arg):
    invalid = False
    try:
        index, name = header_arg.split(':')
    except ValueError:
        invalid = True
    else:
        if index not in all_tables:
            invalid = True

    if invalid:
        raise ValueError(
            'Invalid indexed header {!r}'.format(header_arg))

    storage[index] = name


def main():
    default_down_headers = {}
    for header in DEFAULT_DOWNLOAD_CSV_HEADERS:
        replace_header_arg(default_down_headers, header)

    default_up_headers = {}
    for header in DEFAULT_UPLOAD_CSV_HEADERS:
        replace_header_arg(default_up_headers, header)

    def repr_default_header_arg(category_index, headers):
        table_name = (all_tables[category_index]
                      .__table__.name)
        try:
            return ('    Category {} {!r} with header {!r}'
                    ''.format(category_index, table_name,
                              headers[category_index]))
        except IndexError:
            raise ValueError('Invalid header index {}'
                             ''.format(category_index))

    args = docopt(__doc__.format(
        repr(POSTCODE_CSV_HEADER),
        os.linesep.join(
            repr_default_header_arg(i, default_down_headers)
            for i in all_tables),
        os.linesep.join(
            repr_default_header_arg(str(i), default_up_headers)
            for i in all_tables)))

    ini_file = args['INI_FILE']
    filepath = args['CSV_FILEPATH']
    year = args['YEAR']
    postcode_header = args['POSTCODE_HEADER'] or POSTCODE_CSV_HEADER
    down_headers_args = args['--down-header']
    up_headers_args = args['--up-header']
    dry_run = args['--dry-run']

    down_headers = dict(default_down_headers)
    for down_headers_arg in down_headers_args:
        replace_header_arg(down_headers, down_headers_arg)

    up_headers = dict(default_up_headers)
    for up_headers_arg in up_headers_args:
        replace_header_arg(up_headers, up_headers_arg)

    headers = list(itertools.chain.from_iterable((
        [postcode_header], down_headers.values(), up_headers.values())))

    if len(set(headers)) != len(headers):
        header_copies = {headers.count(v): v for v in headers}
        header_copies = {k: v for k, v in header_copies.items() if k > 1}
        raise ValueError('Duplicate header names for csv {}'
                         ''.format(list(header_copies.values())))

    headers = set(headers)

    try:
        year = datetime.datetime.strptime(year, '%Y').year
    except ValueError:
        raise ValueError('Invalid year {}'.format(year))

    settings = get_settings(ini_file)
    session = init_sqlalchemy(settings)

    def get_postcode_area(postcode_area):
        result = (session.query(PostcodeArea)
                  .filter(PostcodeArea.area == postcode_area)
                  .with_entities('id')
                  .first())
        return result[0] if result else result

    def delete_entries(reading_source, year, postcode_area_id):
        return (session.query(reading_source)
                .filter(reading_source.year == year,
                        reading_source.postcode_area_id == postcode_area_id)
                .delete())

    postcode_areas = dict(get_postcode_areas(session))
    postcode_units = dict(get_postcode_units(session))
    postcode_districts = dict(get_postcode_districts(session))

    def convert_entry_key(entry_key):
        district, sector, unit = entry_key
        return (postcode_districts[district], sector, postcode_units[unit])

    for filepath in sorted(glob.glob(os.path.join(filepath, '*.csv'))):
        _logger.info('Loading file {}'.format(filepath))

        with open(filepath, 'r') as csv_file:
            reader = csv.DictReader(csv_file, delimiter=',', quotechar='"')

            if not headers.issubset(reader.fieldnames):
                missing_headers = headers.difference(reader.fieldnames)
                missing_headers = ', '.join(
                    repr(h) for h in missing_headers)
                raise ValueError('Missing csv headers {} in {}'
                                 ''.format(missing_headers, filepath))

            with transaction.manager:
                rows_entries = {}
                postcode_area = None
                rows_postcodes_districts = set()
                rows_postcodes_units = set()

                for row_i, row in enumerate(reader):
                    row_postcode = row[postcode_header]
                    postcode_parts = split_postcode(row_postcode)
                    if not postcode_parts:
                        raise ValueError(
                            'Invalid postcode {} in file {!r} at row '
                            '{}'.format(row_postcode, filepath, row_i))

                    row_area, row_district, row_sector, row_unit = (
                        postcode_parts)

                    if (postcode_area is not None and
                            postcode_area != row_area):
                        raise ValueError(
                            'Invalid postcode area in file {!r} at row '
                            '{}'.format(filepath, row_i))
                    elif postcode_area is None:
                        postcode_area = row_area

                    rows_postcodes_districts.add(row_district)
                    rows_postcodes_units.add(row_unit)

                    entry_key = (row_district, row_sector, row_unit)

                    for header_source in (down_headers, up_headers):
                        for category, header in header_source.items():
                            entries = rows_entries.setdefault(category, {})
                            entry = entries.setdefault(entry_key, [])
                            try:
                                entry.append(float(row[header]))
                            except ValueError:
                                entry.append(None)

                postcode_area_id = postcode_areas.get(postcode_area)
                if not postcode_area_id:
                    _logger.info('Adding new postcode area {!r}'
                                 ''.format(postcode_area))
                    if dry_run:
                        # To simulate saving
                        postcode_areas[postcode_area] = len(postcode_areas)
                    else:
                        session.add(PostcodeArea(area=postcode_area))
                        _logger.info('Committing...')
                        transaction.commit()
                        postcode_areas[postcode_area] = (
                            get_postcode_area(postcode_area))

                    postcode_area_id = postcode_areas.get(postcode_area)

                new_units = rows_postcodes_units.difference(postcode_units)
                for new_unit in new_units:
                    if dry_run:
                        # To simulate saving
                        postcode_units[new_unit] = len(postcode_units)
                    else:
                        session.add(PostcodeUnit(unit=new_unit))

                if new_units:
                    _logger.info('Adding {} new postcode units'
                                 ''.format(len(new_units)))
                    if not dry_run:
                        _logger.info('Committing...')
                        transaction.commit()
                        postcode_units = dict(get_postcode_units(session))

                new_districts = (rows_postcodes_districts
                                 .difference(postcode_districts))
                for new_district in new_districts:
                    if dry_run:
                        # To simulate saving
                        postcode_districts[new_district] = len(
                            postcode_districts)
                    else:
                        session.add(PostcodeDistrict(district=new_district))

                if new_districts:
                    _logger.info('Adding {} new postcode districts'
                                 ''.format(len(new_districts)))
                    if not dry_run:
                        _logger.info('Committing...')
                        transaction.commit()
                        postcode_districts = dict(
                            get_postcode_districts(session))

                if not dry_run:
                    for category in rows_entries:
                        table = all_tables[category]
                        table_name = table.__table__.name

                        _logger.info('Deleting old entries for table {} '
                                     'for year {}'.format(table_name,
                                                          year))

                        delete_entries(table, year, postcode_area_id)

                    _logger.info('Committing...')
                    transaction.commit()

                new_entries = False
                for category, entries in rows_entries.items():
                    table = all_tables[category]
                    table_name = table.__table__.name

                    new_entry_count = 0
                    for entry_key, entry in entries.items():
                        # Latest values are taken from duplicate row entries
                        download, upload = entry[-2:]

                        if download is None and upload is None:
                            continue

                        district, sector, unit = entry_key

                        district_id = postcode_districts[district]
                        unit_id = postcode_units[unit]

                        new_entry = table(
                            postcode_area_id=postcode_area_id,
                            postcode_district_id=district_id,
                            postcode_sector=sector,
                            postcode_unit_id=unit_id,
                            year=year, download=download, upload=upload)
                        session.add(new_entry)
                        new_entry_count += 1

                    if new_entry_count:
                        _logger.info('Storing {} new entries, for table {}'
                                     ''.format(new_entry_count,
                                               table_name))

                        new_entries = True
                        if dry_run:
                            transaction.abort()
                            new_entries = False
                    else:
                        _logger.info('No updates for postcode area '
                                     '{} within table {}'
                                     ''.format(postcode_area, table_name))

                if new_entries:
                    _logger.info('Committing entries...')
                    transaction.commit()

    _logger.info('Done.')


if __name__ == "__main__":
    main()
