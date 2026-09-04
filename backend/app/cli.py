import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User


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


if __name__ == "__main__":
    main()
