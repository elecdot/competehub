from __future__ import annotations

from marshmallow import Schema, ValidationError, fields

from competehub_api.timezones import product_datetime_as_utc, stored_datetime_as_utc


class StrictBoolean(fields.Boolean):
    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, bool):
            raise ValidationError("Not a valid boolean.")
        return value


class NonBlankString(fields.String):
    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data, **kwargs)
        if not value.strip():
            raise ValidationError("Field may not be blank.")
        return value.strip()


class UtcDateTime(fields.DateTime):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is not None:
            value = stored_datetime_as_utc(value)
        return super()._serialize(value, attr, obj, **kwargs)


class ProductDateTime(UtcDateTime):
    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data, **kwargs)
        return product_datetime_as_utc(value)


def load_payload(schema: Schema, payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError({"_schema": ["A JSON object is required."]})
    return schema.load(payload)
