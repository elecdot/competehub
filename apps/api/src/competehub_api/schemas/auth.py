from __future__ import annotations

from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from competehub_api.models.enums import UserRole


class RegisterSchema(Schema):
    email = fields.String(validate=validate.Length(min=1))
    phone = fields.String(validate=validate.Length(min=1))
    student_no = fields.String(validate=validate.Length(min=1))
    password = fields.String(required=True, load_only=True, validate=validate.Length(min=1))
    display_name = fields.String(allow_none=True)
    role = fields.String(
        load_default=UserRole.STUDENT.value,
        validate=validate.OneOf([UserRole.STUDENT.value]),
    )

    @validates_schema
    def validate_identity(self, data, **kwargs):
        if not any(data.get(field) for field in ("email", "phone", "student_no")):
            raise ValidationError(
                "At least one account identifier is required.",
                field_name="email",
            )


class LoginSchema(Schema):
    account = fields.String(required=True, validate=validate.Length(min=1))
    password = fields.String(required=True, load_only=True, validate=validate.Length(min=1))


class UserSchema(Schema):
    id = fields.Integer(required=True)
    display_name = fields.String(allow_none=True)
    role = fields.String(required=True)


register_schema = RegisterSchema()
login_schema = LoginSchema()
user_schema = UserSchema()
