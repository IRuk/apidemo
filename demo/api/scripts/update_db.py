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
appropriate permissions to update tables on the database. Committing
changes only occurs after each entire file is processed without incident. Each
file must contain all entries for one postal area, other postal areas in the
same file will raise and abort.

Indexed headers:
    Header indexes represent the subset for the header type. Index start at 0
    are separated from the header name by a colon.
    Header with index 0 will use table 0 to populate the 'overall
    average', any subsequent index is used to store subsequent indexes. Care
    must be taken to not apply changes to the wrong table.

    Example 1, '0:Download'
    Example 2, '1:Download < 10Mbit/s'

Default postcode header:
    {0}

Default download header arguments. Format is 'table_index:header':
{1}

Default upload header arguments. Format is 'table_index:header':
{2}
"""
import os
import logging
import glob
import csv
import datetime
from itertools import chain

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
            return ('    Table {!r} at index {} with header {!r}'
                    ''.format(table_name, category_index,
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

    headers = list(chain.from_iterable((
        [postcode_header], down_headers.values(), up_headers.values())))

    if len(set(headers)) != len(headers):
        copied_headers = {headers.count(v): v for v in headers}
        copied_headers = {k: v for k, v in copied_headers.items() if k > 1}
        raise ValueError('Duplicate header names for csv {}'
                         ''.format(list(copied_headers.values())))

    headers = set(headers)

    try:
        year = datetime.datetime.strptime(year, '%Y').year
    except ValueError:
        raise ValueError('Invalid year {}'.format(year))

    settings = get_settings(ini_file)
    session = init_sqlalchemy(settings)

    def get_old_entries(reading_source, year, postcode_area_id):
        return (session.query(reading_source)
                .filter(reading_source.year == year,
                        reading_source.postcode_area_id == postcode_area_id)
                .all())

    for filepath in sorted(glob.glob(os.path.join(filepath, '*.csv'))):
        _logger.info('Loading file {}'.format(filepath))

        postcode_areas = dict(get_postcode_areas(session))
        postcode_units = dict(get_postcode_units(session))
        postcode_districts = dict(get_postcode_districts(session))

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
                new_postcode_units = {}
                new_postcode_districts = {}

                # Required to provide the postcode id to the query used to
                # gather old entries from tables for deletion
                first_row_postcode_area = None
                for first_row in reader:
                    row_postcode = first_row[postcode_header]
                    postcode_parts = split_postcode(row_postcode)
                    if not postcode_parts:
                        raise ValueError(
                            'Invalid postcode {} in file {!r} at row '
                            '{}'.format(row_postcode, filepath, 0))

                    first_row_postcode_area, _, _, _ = postcode_parts
                    break

                if not first_row_postcode_area:
                    continue

                postcode_area = None
                postcode_area_id = postcode_areas.get(first_row_postcode_area)
                if not postcode_area_id:
                    _logger.info('Adding new postcode area {!r}'
                                 ''.format(first_row_postcode_area))

                    postcode_area = PostcodeArea(area=first_row_postcode_area)
                    session.add(postcode_area)
                    session.flush(objects=[postcode_area])
                    postcode_area_id = postcode_area.id

                deletes = []
                for category in all_tables:
                    table = all_tables[category]
                    table_deletes = get_old_entries(table, year,
                                                    postcode_area_id)

                    table_name = table.__table__.name
                    _logger.info('Deleting {} old entries for table {}'
                                 ''.format(len(table_deletes), table_name))

                    deletes.extend(table_deletes)

                all_rows = chain.from_iterable(([first_row], reader))

                blank_entries_count = 0
                for row_i, row in enumerate(all_rows):
                    row_postcode = row[postcode_header]
                    postcode_key = split_postcode(row_postcode)
                    if not postcode_parts:
                        raise ValueError(
                            'Invalid postcode {} in file {!r} at row '
                            '{}'.format(row_postcode, filepath, row_i))
                    postcode_key = tuple(postcode_key)

                    row_area, row_district, row_sector, row_unit = postcode_key

                    if (first_row_postcode_area != row_area):
                        raise ValueError(
                            'Invalid postcode area in file {!r} at row '
                            '{}'.format(filepath, row_i))

                    unit_id = postcode_units.get(row_unit)
                    if unit_id is None:
                        new_postcode_units.setdefault(
                            row_unit, PostcodeUnit(unit=row_unit))

                    district_id = postcode_districts.get(row_district)
                    if district_id is None:
                        new_postcode_districts.setdefault(
                            row_district,
                            PostcodeDistrict(district=row_district))

                    for header_source_i, header_source in enumerate(
                            (down_headers, up_headers)):
                        for category, header in header_source.items():
                            entries = rows_entries.setdefault(category, {})
                            table = all_tables[category]

                            # Added strings purposefully, as placeholders
                            entry = entries.setdefault(
                                postcode_key,
                                table(postcode_area_id=row_area,
                                      postcode_district_id=row_district,
                                      postcode_sector=row_sector,
                                      postcode_unit_id=row_unit,
                                      year=year))

                            try:
                                value = float(row[header])
                            except ValueError:
                                value = None

                            if header_source_i == 0:
                                entry.download = value
                                continue

                            entry.upload = value

                            # Safe to delete since upload header comes after
                            # download header meaning that download value would
                            # be set
                            entry = entries[postcode_key]
                            if entry.upload is None and entry.download is None:
                                entries.pop(postcode_key)
                                blank_entries_count += 1

                _logger.info('Adding {} new postcode units'
                             ''.format(len(new_postcode_units)))
                _logger.info('Adding {} new postcode districts'
                             ''.format(len(new_postcode_districts)))

                session.add_all(new_postcode_units.values())
                session.add_all(new_postcode_districts.values())
                session.flush(objects=new_postcode_units.values())
                session.flush(objects=new_postcode_districts.values())

                for category, entries in rows_entries.items():
                    for entry_key, entry in entries.items():
                        district = entry.postcode_district_id

                        district_id = postcode_districts.get(district)
                        if district_id is None:
                            district_id = new_postcode_districts[district].id

                        unit = entry.postcode_unit_id

                        unit_id = postcode_units.get(unit)
                        if unit_id is None:
                            unit_id = new_postcode_units[unit].id

                        # Remove placeholders in fields
                        entry.postcode_area_id = postcode_area_id
                        entry.postcode_unit_id = unit_id
                        entry.postcode_district_id = district_id

                    table = all_tables[category]
                    table_name = table.__table__.name

                    _logger.info(
                        'Storing {} new entries{} for table {}'
                        ''.format(len(entries),
                                  (' (ignored {} blank entries)'
                                   ''.format(blank_entries_count)
                                   if blank_entries_count else ''),
                                  table_name))

                    session.add_all(entries.values())
                    session.flush(objects=entries.values())

                if dry_run:
                    transaction.abort()
                elif (postcode_area or new_postcode_units or
                      new_postcode_districts or
                      sum(len(g) for g in rows_entries.values())):
                    # Flush actions causes any entries added to
                    # session.delete() to commit, add them last
                    for delete in deletes:
                        session.delete(delete)

                    _logger.info('Committing...')
                    transaction.commit()

    _logger.info('Done.')


if __name__ == "__main__":
    main()
