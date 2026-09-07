import argparse
import asyncio
import getpass
import sys
import uuid
from datetime import datetime

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.api_key_service import create_api_key, revoke_api_key


async def _create_user(email: str, password: str, display_name: str, timezone: str) -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            print(f"User with email {email} already exists", file=sys.stderr)
            raise SystemExit(1)
        user = User(
            email=email,
            hashed_password=hash_password(password),
            display_name=display_name,
            timezone=timezone,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print(f"Created user {user.email} ({user.id})")


async def _create_api_key(
    *, email: str, name: str, scopes: list[str], expires_at: datetime | None
) -> None:
    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is None:
            print(f"User with email {email} not found", file=sys.stderr)
            raise SystemExit(1)
        created = await create_api_key(
            session,
            owner_id=user.id,
            name=name,
            scopes=scopes,
            expires_at=expires_at,
        )
        await session.commit()
        print(f"Created API key {created.record.name} ({created.record.id})")
        print(f"Prefix: {created.record.key_prefix}")
        print(f"Scopes: {','.join(created.record.scopes)}")
        print(f"API key: {created.plaintext_key}")
        print("Store it now; it will never be shown again.")


async def _revoke_api_key(*, key_id: uuid.UUID | None, key_prefix: str | None) -> None:
    async with AsyncSessionLocal() as session:
        record = await revoke_api_key(session, key_id=key_id, key_prefix=key_prefix)
        if record is None:
            print("API key not found", file=sys.stderr)
            raise SystemExit(1)
        await session.commit()
        print(f"Revoked API key {record.name} ({record.key_prefix})")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_user_parser = subparsers.add_parser("create-user", help="Create a new user")
    create_user_parser.add_argument("--email", required=True)
    create_user_parser.add_argument("--display-name", required=True)
    create_user_parser.add_argument("--timezone", default="Europe/Prague")
    create_user_parser.add_argument(
        "--password", default=None, help="If omitted, you will be prompted"
    )

    create_api_key_parser = subparsers.add_parser("create-api-key", help="Create a machine API key")
    create_api_key_parser.add_argument("--email", required=True)
    create_api_key_parser.add_argument("--name", required=True)
    create_api_key_parser.add_argument("--scopes", required=True, help="Comma-separated scopes")
    create_api_key_parser.add_argument("--expires-at", default=None, help="Optional ISO datetime")

    revoke_api_key_parser = subparsers.add_parser("revoke-api-key", help="Revoke a machine API key")
    group = revoke_api_key_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--id", dest="key_id", default=None)
    group.add_argument("--prefix", dest="key_prefix", default=None)

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "create-user":
        password = args.password or getpass.getpass("Password: ")
        if not password:
            print("Password must not be empty", file=sys.stderr)
            raise SystemExit(1)
        asyncio.run(_create_user(args.email, password, args.display_name, args.timezone))
    elif args.command == "create-api-key":
        scopes = [scope.strip() for scope in args.scopes.split(",") if scope.strip()]
        expires_at = datetime.fromisoformat(args.expires_at) if args.expires_at else None
        asyncio.run(
            _create_api_key(
                email=args.email,
                name=args.name,
                scopes=scopes,
                expires_at=expires_at,
            )
        )
    elif args.command == "revoke-api-key":
        key_id = uuid.UUID(args.key_id) if args.key_id else None
        asyncio.run(_revoke_api_key(key_id=key_id, key_prefix=args.key_prefix))


if __name__ == "__main__":
    main()
