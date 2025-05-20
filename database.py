from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base



DB_NAME = 'assets/mafia.db'
engine = create_engine(f"sqlite:///{DB_NAME}", echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
from models.base import Base


def init_db():
    Base.metadata.create_all(bind=engine)