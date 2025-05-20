from sqlalchemy import Column, Integer, ForeignKey, String
from models.base import Base

class Registration(Base):
    __tablename__ = "registrations"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    game_id = Column(Integer, ForeignKey('games.id'))
    payment_type = Column(String)
    present = Column(Integer, default=1)