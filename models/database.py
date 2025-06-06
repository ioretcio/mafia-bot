from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from models.base import Base


DB_NAME = 'assets/mafia.db'
engine = create_engine(f"sqlite:///{DB_NAME}", echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



def init_db():
    Base.metadata.create_all(bind=engine)

init_db()