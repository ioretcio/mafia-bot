from sqlalchemy import Column, Integer, String, Text
from database import SessionLocal
from models.base import Base
from datetime import date
from sqlalchemy.orm import relationship
from models.registration import Registration

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
        game = Game(
            date=date,
            time=time,
            location=location,
            type=type_,
            host=host,
            media=media,
            price=price,
            player_limit=player_limit,
            description=description
        )
        session.add(game)
        session.commit()
        session.refresh(game)  # 👈 ОБОВʼЯЗКОВО! отримати id ДО закриття сесії
        session.close()
        return game

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