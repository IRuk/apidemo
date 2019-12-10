from colander import Length
from colander import SchemaNode
from colander import SequenceSchema
from colander import Mapping

from ._common import PrettyQuerySchema
from .types import String


class AverageQuerySchema(PrettyQuerySchema):
    """A connection speed average query object."""
    connection = SchemaNode(
        String(),
        missing='average',
        location='querystring',
        description='connection type')
    postcode = SchemaNode(
        String(),
        location='querystring',
        description='postal code with no spaces')


class AverageItemSchema(SchemaNode):
    """A connection speed averages."""
    schema_type = Mapping

    connection = SchemaNode(
        String(),
        validator=Length(1, 5),
        description='Connection type.')
    download = SchemaNode(
        String(),
        missing=None,
        validator=Length(1, 256),
        description='Download reading.')
    upload = SchemaNode(
        String(),
        missing=None,
        validator=Length(1, 256),
        description='Upload reading.')


class AverageItemsSchema(SequenceSchema):
    """A series of connection speed averages."""

    average_item = AverageItemSchema()
