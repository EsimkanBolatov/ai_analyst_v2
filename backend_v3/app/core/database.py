from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app import models  # noqa: F401
from app.models.base import Base
from app.models.role import DEFAULT_ROLES, Role

engine = create_engine(settings.sqlalchemy_database_uri, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        for role_name, description in DEFAULT_ROLES.items():
            exists = db.query(Role).filter(Role.name == role_name).first()
            if not exists:
                db.add(Role(name=role_name, description=description))
        db.commit()

    if settings.seed_test_data:
        from app.core.test_seed import seed_test_data

        seed_test_data(SessionLocal)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
