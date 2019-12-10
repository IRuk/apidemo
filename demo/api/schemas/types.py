from colander import null
from colander import String


class _NoneMixin(object):
    """Serializes None as colander.null.

    Colander raises an error if the value of a serialized field is None. This
    mixin can be used to transparently convert None to colander.null.
    """

    def serialize(self, node, appstruct):
        if appstruct is None:
            return null
        return super(_NoneMixin, self).serialize(node, appstruct)


class String(_NoneMixin, String):
    """Serializes None as colander.null.

    The default String serializes None as "None".
    """

    pass
