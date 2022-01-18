# coding: utf-8
from sqlalchemy import Column, Float, Integer, Table, Text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.ext.declarative import declarative_base
from valuation import db

Base = declarative_base()
metadata = Base.metadata
Base.query = db.session.query_property()

class Player(Base):
    __tablename__ = 'player'

    id = Column(Integer, primary_key=True)
    first_name = Column(Text)
    second_name = Column(Text)
    team = Column(Text)
    position = Column(Text)
    points_per_game = Column(Float)
    total_points = Column(Integer)
    minutes = Column(Integer)
    now_cost = Column(Float)
    points_per_90 = Column(Float)
    points_per_mil = Column(Float)
    element = Column(Integer)
    VPM90 = Column(Float)


t_record = Table(
    'record', metadata,
    Column('first_name', Text),
    Column('second_name', Text),
    Column('element', Integer),
    Column('fixture', Integer),
    Column('opponent_team', Integer),
    Column('total_points', Integer),
    Column('was_home', TINYINT(1)),
    Column('kickoff_time', Text),
    Column('round', Integer),
    Column('minutes', Integer),
    Column('goals_scored', Integer),
    Column('assists', Integer),
    Column('value', Float),
    Column('VPM90', Float)
)
