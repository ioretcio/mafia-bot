from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from datetime import datetime
from models.base import Base
from database import SessionLocal

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    game_id = Column(Integer, ForeignKey('games.id'), nullable=True)
    date = Column(DateTime, default=datetime.utcnow)
    amount = Column(Integer)
    payment_type = Column(String)
    status = Column(String, default="pending")
    order_reference = Column(String, unique=True)
    comment = Column(Text)
    raw_response = Column(Text)

    @staticmethod
    def get_user_payments(user_id):
        session = SessionLocal()
        payments = session.query(Payment).filter_by(user_id=user_id).all()
        session.close()
        return payments

    @staticmethod
    def get_pending_by_user_and_game(user_id, game_id):
        session = SessionLocal()
        payment = session.query(Payment).filter_by(
            user_id=user_id, game_id=game_id, status="pending"
        ).first()
        session.close()
        return payment

    @staticmethod
    def update_status_by_reference(order_reference, new_status):
        session = SessionLocal()
        payment = session.query(Payment).filter_by(order_reference=order_reference).first()
        if payment:
            payment.status = new_status
            session.commit()
        session.close()