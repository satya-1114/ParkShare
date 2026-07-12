"""Create the initial ADMIN account.

Public ADMIN registration is intentionally blocked (see AuthService.register),
so the first administrator must be provisioned out-of-band with this script.

Credentials are read from environment variables or, if absent, prompted for
interactively. Passwords are never accepted from source and never printed.

Usage:
    ADMIN_EMAIL=admin@example.com \
    ADMIN_PASSWORD='...' \
    ADMIN_FULL_NAME='Site Admin' \
    python -m scripts.create_admin

Run from the backend/ directory.
"""
import asyncio
import getpass
import os
import sys

from app.core.security import hash_password
from app.database.session import AsyncSessionLocal
from app.models.user import User, UserRole
from app.repositories.user import UserRepository


async def create_admin() -> int:
    email = (os.getenv("ADMIN_EMAIL") or input("Admin email: ")).strip().lower()
    full_name = (os.getenv("ADMIN_FULL_NAME") or input("Admin full name: ")).strip()
    phone = (os.getenv("ADMIN_PHONE") or input("Admin phone: ")).strip()
    password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Admin password: ")

    if not email or not password or not full_name:
        print("ERROR: email, full name, and password are required.")
        return 1
    if len(password) < 8:
        print("ERROR: password must be at least 8 characters.")
        return 1

    async with AsyncSessionLocal() as session:
        users = UserRepository(session)
        existing = await users.get_by_email(email)
        if existing:
            if existing.role == UserRole.ADMIN:
                print(f"Admin already exists: {email} (no changes made).")
            else:
                print(
                    f"A user already exists with {email} but role={existing.role.value}. "
                    "Refusing to modify it."
                )
            return 0

        admin = User(
            full_name=full_name,
            email=email,
            phone=phone or None,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        await users.create(admin)
        print(f"Admin account created successfully: {email}")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(create_admin()))
