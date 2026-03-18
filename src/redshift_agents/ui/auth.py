"""
Cognito authentication utilities for the Streamlit UI.

Provides:
- Cognito sign-in (USER_PASSWORD_AUTH)
- JWT user_id extraction (cognito:username → email fallback)
- Identity Pool credential exchange (JWT → temp AWS creds)
- Token refresh
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any

import boto3

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "")
COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID", "")
COGNITO_IDENTITY_POOL_ID = os.getenv("COGNITO_IDENTITY_POOL_ID", "")
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode the payload section of a JWT (no signature verification).

    Cognito/Identity Pool handle verification — we only need the claims
    for display and user_id extraction.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT: expected 3 dot-separated parts")

    payload_b64 = parts[1]
    # Add padding if needed
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding

    payload_bytes = base64.urlsafe_b64decode(payload_b64)
    return json.loads(payload_bytes)


def extract_user_id(id_token: str) -> str:
    """Extract a human-readable user identifier from a Cognito ID token.

    Delegates to ``extract_user_id_from_payload`` — prefers email, then
    preferred_username, then cognito:username, then sub.
    """
    payload = decode_jwt_payload(id_token)
    return extract_user_id_from_payload(payload)


def extract_user_id_from_payload(payload: dict[str, Any]) -> str:
    """Extract a human-readable user identifier from an already-decoded JWT payload.

    Preference order: email → preferred_username → cognito:username (may be a UUID
    for admin-created users) → sub.
    """
    for claim in ("email", "preferred_username", "cognito:username", "sub"):
        value = payload.get(claim)
        if value:
            return str(value)

    raise ValueError("JWT payload contains no usable identity claim")


# ---------------------------------------------------------------------------
# Cognito sign-in
# ---------------------------------------------------------------------------


def cognito_sign_in(username: str, password: str, new_password: str | None = None) -> dict[str, str]:
    """Authenticate via Cognito USER_PASSWORD_AUTH flow.

    Handles the ``NEW_PASSWORD_REQUIRED`` challenge that occurs on first
    login with a temporary password.

    Returns a dict with ``id_token``, ``access_token``, and ``refresh_token``
    on success.  Returns ``{"challenge": "NEW_PASSWORD_REQUIRED", "session": ...}``
    when a new password is needed.  Raises on authentication failure.
    """
    client = boto3.client("cognito-idp", region_name=AWS_REGION)
    response = client.initiate_auth(
        ClientId=COGNITO_APP_CLIENT_ID,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": password,
        },
    )

    # Handle NEW_PASSWORD_REQUIRED challenge (first login with temp password)
    if response.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
        if not new_password:
            return {
                "challenge": "NEW_PASSWORD_REQUIRED",
                "session": response["Session"],
            }
        # Respond to the challenge with the new password
        challenge_response = client.respond_to_auth_challenge(
            ClientId=COGNITO_APP_CLIENT_ID,
            ChallengeName="NEW_PASSWORD_REQUIRED",
            Session=response["Session"],
            ChallengeResponses={
                "USERNAME": username,
                "NEW_PASSWORD": new_password,
            },
        )
        result = challenge_response["AuthenticationResult"]
    else:
        result = response["AuthenticationResult"]

    return {
        "id_token": result["IdToken"],
        "access_token": result["AccessToken"],
        "refresh_token": result["RefreshToken"],
    }


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------


def refresh_tokens(refresh_token: str) -> dict[str, str]:
    """Use a refresh token to obtain new ID and access tokens.

    Returns a dict with ``id_token`` and ``access_token``.
    Raises on failure (caller should redirect to sign-in).
    """
    client = boto3.client("cognito-idp", region_name=AWS_REGION)
    response = client.initiate_auth(
        ClientId=COGNITO_APP_CLIENT_ID,
        AuthFlow="REFRESH_TOKEN_AUTH",
        AuthParameters={
            "REFRESH_TOKEN": refresh_token,
        },
    )
    result = response["AuthenticationResult"]
    return {
        "id_token": result["IdToken"],
        "access_token": result["AccessToken"],
    }


# ---------------------------------------------------------------------------
# Identity Pool credential exchange
# ---------------------------------------------------------------------------


def get_identity_pool_credentials(id_token: str) -> dict[str, str]:
    """Exchange a Cognito ID token for temporary AWS credentials via the
    Identity Pool.

    Returns a dict with ``AccessKeyId``, ``SecretKey``, ``SessionToken``.
    """
    provider_key = (
        f"cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
    )

    ci_client = boto3.client("cognito-identity", region_name=AWS_REGION)

    # Step 1: GetId
    identity_response = ci_client.get_id(
        IdentityPoolId=COGNITO_IDENTITY_POOL_ID,
        Logins={provider_key: id_token},
    )
    identity_id = identity_response["IdentityId"]

    # Step 2: GetCredentialsForIdentity
    creds_response = ci_client.get_credentials_for_identity(
        IdentityId=identity_id,
        Logins={provider_key: id_token},
    )
    creds = creds_response["Credentials"]
    return {
        "AccessKeyId": creds["AccessKeyId"],
        "SecretKey": creds["SecretKey"],
        "SessionToken": creds["SessionToken"],
    }


def create_authenticated_session(id_token: str) -> boto3.Session:
    """Create a boto3 Session using Identity Pool credentials derived from
    the given Cognito ID token."""
    creds = get_identity_pool_credentials(id_token)
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretKey"],
        aws_session_token=creds["SessionToken"],
        region_name=AWS_REGION,
    )
