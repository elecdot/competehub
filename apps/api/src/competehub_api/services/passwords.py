from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.low_level import Type
from werkzeug.security import check_password_hash

ARGON2ID_HASHER = PasswordHasher(
    time_cost=2,
    memory_cost=19_456,
    parallelism=1,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def create_password_hash(password: str) -> str:
    return ARGON2ID_HASHER.hash(password)


def verify_password_hash(password_hash: str, password: str) -> bool:
    if password_hash.startswith("$argon2id$"):
        try:
            return ARGON2ID_HASHER.verify(password_hash, password)
        except (InvalidHashError, VerificationError):
            return False
    return check_password_hash(password_hash, password)


def password_hash_needs_upgrade(password_hash: str) -> bool:
    if not password_hash.startswith("$argon2id$"):
        return True
    try:
        return ARGON2ID_HASHER.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True
