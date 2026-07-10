from __future__ import annotations

from marshmallow import Schema, ValidationError, fields


class StrictBoolean(fields.Boolean):
    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, bool):
            raise ValidationError("Not a valid boolean.")
        return value


def load_payload(schema: Schema, payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError({"_schema": ["A JSON object is required."]})
    return schema.load(payload)
