from marshmallow import Schema, fields, validate


class RegisterSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=64))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=128), load_only=True)
    email = fields.Email(load_default=None)
    phone = fields.Str(load_default=None)
    student_no = fields.Str(load_default=None)
    role = fields.Str(load_default="student", validate=validate.OneOf(["student", "teacher", "organizer"]))


class LoginSchema(Schema):
    account = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)

