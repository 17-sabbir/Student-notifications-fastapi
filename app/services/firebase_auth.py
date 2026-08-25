import firebase_admin
from firebase_admin import auth, credentials
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.core.security import get_password_hash
import uuid


if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)


class FirebaseAuthService:
    @staticmethod
    async def verify_id_token(id_token: str) -> dict:
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            raise ValueError(f"Invalid Firebase token: {e}")

    @staticmethod
    async def get_or_create_user(db: AsyncSession, firebase_user: dict) -> User:
        uid = firebase_user.get("uid")
        email = firebase_user.get("email")

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                hashed_password=get_password_hash(uuid.uuid4().hex),
                is_verified=firebase_user.get("email_verified", False),
                is_active=True,
                role="user",
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        else:
            user.is_verified = firebase_user.get("email_verified", False)
            await db.commit()
            await db.refresh(user)

        return user

    @staticmethod
    async def create_pending_admin(db: AsyncSession, email: str, password: str) -> User:
        try:
            firebase_user = auth.create_user(email=email, password=password, email_verified=False)
        except auth.UidAlreadyExistsError:
            raise ValueError("A user with this email already exists in Firebase")
        except Exception as e:
            raise ValueError(f"Failed to create Firebase user: {e}")

        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            existing_user.role = "admin"
            existing_user.is_verified = False
            existing_user.is_active = True
            await db.commit()
            await db.refresh(existing_user)
            return existing_user

        user = User(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=get_password_hash(uuid.uuid4().hex),
            is_verified=False,
            is_active=True,
            role="admin",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
