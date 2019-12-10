import unittest

from colander import Invalid

from ..schemas import AverageQuerySchema


class AverageQuerySchemaTests(unittest.TestCase):

    def test_deserialisation(self):
        with self.assertRaisesRegexp(Invalid, '.+postcode.+'):
            AverageQuerySchema().deserialize({})
