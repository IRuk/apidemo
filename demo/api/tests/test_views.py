import json
import unittest
from unittest import mock
import os
import re

from pyramid import testing
from pyramid.httpexceptions import HTTPBadRequest

from demo.api.schemas import AverageQuerySchema
from demo.api.views import demo_home
from demo.api.views import get_averages
from demo.api.views import demo_average
from demo.api.views import clear_postcode_caching

fixtures_basedir = os.path.join(os.path.dirname(__file__), 'fixtures')


class TestBase(unittest.TestCase):

    def get_fixture(self, filename):
        with open(os.path.join(fixtures_basedir, filename)) as fixture:
            return json.loads(fixture.read())

    def make_request(self, data):
        self.request.validated = AverageQuerySchema().deserialize(data)

    def make_request_params(self, data):
        self.request.params = AverageQuerySchema().deserialize(data)


class PageViewsTests(TestBase):
    def setUp(self):
        self.config = testing.setUp()
        self.request = testing.DummyRequest()

    def tearDown(self):
        testing.tearDown()
        clear_postcode_caching()

    @mock.patch('demo.api.views._table_counts')
    def test_home_view(self, table_counts):
        fake_table_counts = [('foo', 0)]
        table_counts.return_value = fake_table_counts

        response = demo_home(self.request)
        response = dict(response)

        self.assertTrue('version' in response)
        self.assertTrue('database_row_counts' in response)
        self.assertTrue(re.match(r'^[\d\.]+$', response['version']))
        self.assertEqual(response['database_row_counts'], fake_table_counts)

    @mock.patch('demo.api.views._averages.get_postcode_units')
    @mock.patch('demo.api.views._averages.get_postcode_districts')
    @mock.patch('demo.api.views._averages.get_postcode_areas')
    @mock.patch('demo.api.views._averages._get_averages')
    def test_demo_average(
            self, fake_get_averages, fake_areas, fake_districts, fake_units):
        fake_areas.return_value = [('AB', 1)]
        fake_districts.return_value = [('10', 1)]
        fake_units.return_value = [('AU', 1)]
        fake_results = [
            {'connection': 'average',
             'upload': '0.0',
             'download': '0.0'}]
        fake_get_averages.return_value = fake_results

        self.make_request_params(self.get_fixture('sample_input.json'))
        response = demo_average(self.request)

        self.assertEqual(
            response,
            {'message': '', 'results': [{'connection': 'average',
                                         'download': '0.0', 'upload': '0.0'}]})
        self.assertEqual(fake_get_averages.call_count, 1)

    def test_demo_average_bad_postcode(self):
        self.make_request_params(
            self.get_fixture('invalid_postcode_input.json'))
        response = demo_average(self.request)

        self.assertEqual(
            response,
            {'results': [], 'message': 'Invalid postal code.'})

    @mock.patch('demo.api.views._averages.get_postcode_units')
    @mock.patch('demo.api.views._averages.get_postcode_districts')
    @mock.patch('demo.api.views._averages.get_postcode_areas')
    def test_demo_average_bad_connection(
            self, fake_areas, fake_districts, fake_units):
        fake_areas.return_value = [('AB', 1)]
        fake_districts.return_value = [('10', 1)]
        fake_units.return_value = [('AU', 1)]

        self.make_request_params(
            self.get_fixture('invalid_connection_input.json'))
        response = demo_average(self.request)

        self.assertEqual(
            response,
            {'results': [], 'message': 'Invalid connection.'})

    @mock.patch('demo.api.views._averages.get_postcode_units')
    @mock.patch('demo.api.views._averages.get_postcode_districts')
    @mock.patch('demo.api.views._averages.get_postcode_areas')
    @mock.patch('demo.api.views._averages._get_averages')
    def test_demo_average_empty_postcode_caching(
            self, fake_get_averages, fake_areas, fake_districts, fake_units):
        fake_areas.return_value = []
        fake_districts.return_value = []
        fake_units.return_value = []

        self.make_request_params(
            self.get_fixture('sample_input.json'))
        response = demo_average(self.request)

        self.assertEqual(response, {'results': [], 'message': 'No results.'})
        self.assertEqual(fake_get_averages.call_count, 0)


class GetAveragesTests(TestBase):
    def setUp(self):
        self.config = testing.setUp()
        self.request = testing.DummyRequest()

    def tearDown(self):
        testing.tearDown()
        clear_postcode_caching()

    def test_get_averages_bad_postcode(self):
        self.make_request(self.get_fixture('invalid_postcode_input.json'))

        self.assertRaises(HTTPBadRequest, get_averages, self.request)

    @mock.patch('demo.api.views._averages.get_postcode_units')
    @mock.patch('demo.api.views._averages.get_postcode_districts')
    @mock.patch('demo.api.views._averages.get_postcode_areas')
    @mock.patch('demo.api.views._averages._get_averages')
    def test_get_averages_no_postcode_parts(
            self, fake_get_averages, fake_areas, fake_districts, fake_units):
        fake_areas.return_value = []
        fake_districts.return_value = []
        fake_units.return_value = []

        self.make_request(self.get_fixture('sample_input.json'))
        response = get_averages(self.request)

        self.assertEqual(response, [])
        self.assertEqual(fake_get_averages.call_count, 0)

    @mock.patch('demo.api.views._averages.get_postcode_units')
    @mock.patch('demo.api.views._averages.get_postcode_districts')
    @mock.patch('demo.api.views._averages.get_postcode_areas')
    @mock.patch('demo.api.views._averages._get_averages')
    def test_get_averages(
            self, fake_get_averages, fake_areas, fake_districts, fake_units):
        fake_areas.return_value = [('AB', 1)]
        fake_districts.return_value = [('10', 1)]
        fake_units.return_value = [('AU', 1)]
        fake_results = [
            {'connection': 'average',
             'upload': '0.0',
             'download': '0.0'}]
        fake_get_averages.return_value = fake_results

        self.make_request(self.get_fixture('sample_input.json'))
        response = get_averages(self.request)

        self.assertEqual(response, fake_results)
