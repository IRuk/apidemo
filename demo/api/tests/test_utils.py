import unittest

from demo.api.common.utils.postcodes import split_postcode


class SplitPostcodeTests(unittest.TestCase):

    def test_split_postcode(self):
        self.assertEqual(split_postcode('AB101AU'), ('AB', '10', '1', 'AU'))

    def test_split_postcode_minimums(self):
        self.assertEqual(split_postcode('A11AA'), ('A', '1', '1', 'AA'))

    def test_split_postcode_distric_letter(self):
        self.assertEqual(split_postcode('AB1B1AU'), ('AB', '1B', '1', 'AU'))

    def test_split_postcode_invalid(self):
        self.assertEqual(split_postcode('AB1BFFFF1AU'), None)

    def test_split_postcode_spaces(self):
        self.assertEqual(split_postcode('AB1B   1AU'), ('AB', '1B', '1', 'AU'))

    def test_split_postcode_space(self):
        self.assertEqual(split_postcode('AB1B 1AU'), ('AB', '1B', '1', 'AU'))

    def test_split_postcode_blank(self):
        self.assertEqual(split_postcode(''), None)

    def test_split_postcode_lower_letters(self):
        self.assertEqual(split_postcode('ab1b1au'), ('AB', '1B', '1', 'AU'))

    def test_split_postcode_none(self):
        self.assertRaises(TypeError, split_postcode, None)
