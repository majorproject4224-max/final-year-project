from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser


class ObjectJSONParser(JSONParser):
    """Every JSON endpoint accepts an object; malformed shapes fail before view logic."""

    def parse(self, stream, media_type=None, parser_context=None):
        value = super().parse(stream, media_type, parser_context)
        if not isinstance(value, dict):
            raise ParseError("Send a JSON object.")
        return value
