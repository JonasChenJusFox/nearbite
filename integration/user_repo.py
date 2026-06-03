"""MongoDB CRUD for user accounts, credentials, and persisted questionnaire profiles."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime

from integration.db import get_collection
from integration.user_profile_model import build_profile_text, normalize_answers
from embeddings.vectorizer import DEFAULT_EMBEDDING_MODEL

users_collection = get_collection("users")
profiles_collection = get_collection("user_profiles")
PASSWORD_HASH_PREFIX = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 260000


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"{PASSWORD_HASH_PREFIX}${PASSWORD_HASH_ITERATIONS}${salt}${digest}"


def _verify_password(password: str, stored_value: object) -> bool:
    stored_text = str(stored_value or "")
    parts = stored_text.split("$")
    if len(parts) != 4 or parts[0] != PASSWORD_HASH_PREFIX:
        return hmac.compare_digest(password, stored_text)

    _prefix, iteration_text, salt, expected_digest = parts
    try:
        iterations = int(iteration_text)
    except ValueError:
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(digest, expected_digest)


def _password_value(user: dict) -> object:
    return user.get("password_hash") or user.get("password")


def _store_password_hash(username: str, password: str) -> str:
    password_hash = _hash_password(password)
    users_collection.update_one(
        {"username": username},
        {
            "$set": {
                "password_hash": password_hash,
                "password": None,
                "updated_at": datetime.utcnow(),
            }
        },
    )
    return password_hash


def create_user(username: str, email: str, password: str, display_name: str) -> None:
    users_collection.insert_one(
        {
            "username": username,
            "email": email,
            "password_hash": _hash_password(password),
            "display_name": display_name,
            "created_at": datetime.utcnow(),
        }
    )


def find_user_by_username(username: str) -> dict | None:
    return users_collection.find_one({"username": username})


def find_user_by_credentials(username: str, password: str) -> dict | None:
    user = find_user_by_username(username)
    if not user or not _verify_password(password, _password_value(user)):
        return None

    if user.get("password") and not user.get("password_hash"):
        user["password_hash"] = _store_password_hash(username, password)
        user["password"] = None

    return user


def reset_user_password(username: str, new_password: str) -> None:
    users_collection.update_one(
        {"username": username},
        {
            "$set": {
                "password_hash": _hash_password(new_password),
                "password": None,
                "updated_at": datetime.utcnow(),
            }
        },
    )


def save_user_profile(username: str, questionnaire_answers: dict) -> None:
    normalized_features = normalize_answers(questionnaire_answers)
    profile_text = build_profile_text(questionnaire_answers)

    profiles_collection.update_one(
        {"username": username},
        {
            "$set": {
                "username": username,
                "raw_answers": questionnaire_answers,
                "normalized_features": normalized_features,
                "profile_text": profile_text,
                "latest_embedding": None,
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )


def get_user_profile(username: str) -> dict | None:
    return profiles_collection.find_one({"username": username})


def update_latest_embedding(username: str, embedding_vector: list[float]) -> None:
    profiles_collection.update_one(
        {"username": username},
        {
            "$set": {
                "latest_embedding": {
                    "vector": embedding_vector,
                    "model_name": DEFAULT_EMBEDDING_MODEL,
                    "updated_at": datetime.utcnow(),
                },
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )
