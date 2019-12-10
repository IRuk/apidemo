from colander import Boolean
from colander import MappingSchema
from colander import SchemaNode


class PrettyQuerySchema(MappingSchema):
    pretty = SchemaNode(
        Boolean(),
        missing=False,
        location='querystring',
        description='readable output formatting')
