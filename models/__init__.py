from .user import User
from .game import Game
from .payment import Payment
from sqlalchemy.orm import relationship

User.payments = relationship("Payment", back_populates="user")
Game.payments = relationship("Payment", back_populates="game")
Payment.user = relationship("User", back_populates="payments")
Payment.game = relationship("Game", back_populates="payments")