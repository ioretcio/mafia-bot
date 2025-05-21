from sqlalchemy import Column, Integer, String, Text, ForeignKey
from database import SessionLocal
from datetime import date
from models.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    full_name = Column(String)
    photo = Column(String)
    status = Column(String, default="Новичок")
    games_played = Column(Integer, default=0)
    bonus_points = Column(Integer, default=0)


    # ------- CRUD -------
    @staticmethod
    def all():
        session = SessionLocal()
        users = session.query(User).all()
        session.close()
        return users

    @staticmethod
    def get(user_id):
        session = SessionLocal()
        user = session.query(User).get(user_id)
        session.close()
        return user

    @staticmethod
    def get_by_tg_id(tg_id):
        session = SessionLocal()
        user = session.query(User).filter_by(tg_id=tg_id).first()
        session.close()
        return user

    @staticmethod
    def get_payments(user_id):
        session = SessionLocal()
        payments = session.query(Payment).filter_by(user_id=user_id).all()
        session.close()
        return payments

    @staticmethod
    def delete(user_id):
        session = SessionLocal()
        user = session.query(User).get(user_id)
        if user:
            session.delete(user)
            session.commit()
        session.close()

    @staticmethod
    def update_status(user_id, status):
        session = SessionLocal()
        user = session.query(User).get(user_id)
        if user:
            user.status = status
            session.commit()
        session.close()

    @staticmethod
    def get_or_create(tg_id, username=None, full_name=None):
        session = SessionLocal()
        user = session.query(User).filter_by(tg_id=tg_id).first()
        if user:
            session.close()
            return user
        user = User(tg_id=tg_id, username=username, full_name=full_name)
        session.add(user)
        session.commit()
        session.refresh(user)
        session.close()
        return user