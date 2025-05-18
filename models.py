from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base, SessionLocal
from datetime import date

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

class Game(Base):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True)
    date = Column(String)
    time = Column(String)
    location = Column(String)
    type = Column(String)
    host = Column(String)
    price = Column(Integer, default=0)
    player_limit = Column(Integer, default=0)
    description = Column(Text)
    media = Column(String)

    @staticmethod
    def all_upcoming():
        session = SessionLocal()
        today = date.today().isoformat()
        events = session.query(Game).filter(Game.date >= today).order_by(Game.date).all()
        session.close()
        return events

    @staticmethod
    def get(event_id):
        session = SessionLocal()
        event = session.query(Game).get(event_id)
        session.close()
        return event

    @staticmethod
    def add(date, time, location, type_, host, media, price, player_limit, description):
        session = SessionLocal()
        event = Game(
            date=date, time=time, location=location, type=type_, host=host,
            media=media, price=price, player_limit=player_limit, description=description
        )
        session.add(event)
        session.commit()
        session.close()
        return event

    @staticmethod
    def update(event_id, date, time, location, type_, host, price, player_limit, description, media):
        session = SessionLocal()
        event = session.query(Game).get(event_id)
        if event:
            event.date = date
            event.time = time
            event.location = location
            event.type = type_
            event.host = host
            event.price = price
            event.player_limit = player_limit
            event.description = description
            if media is not None:
                event.media = media
            session.commit()
        session.close()

    @staticmethod
    def delete(event_id):
        session = SessionLocal()
        event = session.query(Game).get(event_id)
        if event:
            session.delete(event)
            session.commit()
        session.close()

    @staticmethod
    def players_count(event_id):
        session = SessionLocal()
        count = session.query(Registration).filter_by(game_id=event_id).count()
        session.close()
        return count

class Registration(Base):
    __tablename__ = "registrations"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    game_id = Column(Integer, ForeignKey('games.id'))
    payment_type = Column(String)
    present = Column(Integer, default=1)

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    game_id = Column(Integer, ForeignKey('games.id'), nullable=True)
    date = Column(String)
    amount = Column(Integer)
    payment_type = Column(String)
    comment = Column(Text)

    @staticmethod
    def get_user_payments(user_id):
        session = SessionLocal()
        payments = session.query(Payment).filter_by(user_id=user_id).all()
        session.close()
        return payments
