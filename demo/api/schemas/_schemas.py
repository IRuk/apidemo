from colander import SchemaNode
from colander import MappingSchema
from colander import Mapping

from ._common import PrettyQuerySchema
from .types import String


class SchemaQuerySchema(PrettyQuerySchema):
    name = SchemaNode(
        String(),
        location='path',
        description='The name of the schema')


class SchemaAttributeSchema(MappingSchema):
    name = SchemaNode(
        String(),
        description='The name of the schema')
    url = SchemaNode(
        String(),
        description='The URL of the schema')

    def schema_type(self):
        return Mapping()
