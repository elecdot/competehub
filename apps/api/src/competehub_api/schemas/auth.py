from __future__ import annotations

from marshmallow import Schema, ValidationError, fields, pre_load, validate

IDENTITY_TYPES = ("email", "phone", "student_no")


class IdentityAliasSchema(Schema):
    @pre_load
    def normalize_identity_alias(self, data, **kwargs):
        if "identifier" not in data:
            return data
        normalized = dict(data)
        identifier = normalized.pop("identifier")
        if "identity" in normalized and normalized["identity"] != identifier:
            raise ValidationError({"identity": ["Identity and identifier must match."]})
        normalized["identity"] = identifier
        return normalized


class RegisterSchema(IdentityAliasSchema):
    identity_type = fields.String(
        required=True,
        validate=validate.OneOf(["email"]),
    )
    identity = fields.String(required=True, validate=validate.Length(min=1))
    password = fields.String(required=True, load_only=True)
    display_name = fields.String(allow_none=True)


class VerifySchema(IdentityAliasSchema):
    identity_type = fields.String(required=True, validate=validate.OneOf(["email"]))
    identity = fields.String(required=True, validate=validate.Length(min=1))
    code = fields.String(required=True, validate=validate.Length(min=1))


class ResendVerificationSchema(IdentityAliasSchema):
    identity_type = fields.String(required=True, validate=validate.OneOf(["email"]))
    identity = fields.String(required=True, validate=validate.Length(min=1))


class LoginSchema(IdentityAliasSchema):
    identity_type = fields.String(required=True, validate=validate.OneOf(IDENTITY_TYPES))
    identity = fields.String(required=True, validate=validate.Length(min=1))
    password = fields.String(required=True, load_only=True)


class UserSchema(Schema):
    id = fields.Integer(required=True)
    display_name = fields.String(allow_none=True)
    role = fields.String(required=True)
    capabilities = fields.Method("get_capabilities")

    def get_capabilities(self, user):
        if user.role == "student":
            return []
        return list(user.capabilities or [])


class AuthCapabilitiesSchema(Schema):
    public_email_registration_enabled = fields.Boolean(required=True)


register_schema = RegisterSchema()
verify_schema = VerifySchema()
resend_verification_schema = ResendVerificationSchema()
login_schema = LoginSchema()
user_schema = UserSchema()
auth_capabilities_schema = AuthCapabilitiesSchema()
