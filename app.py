from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_sslify import SSLify
from dataclasses import asdict
from ftplib import error_temp
from select import select
from flask import render_template, request
import requests
import json 
import math 
import pandas as pd
import plotly
import plotly.express as px
from sqlalchemy import Column, Float, Integer, Table, Text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
load_dotenv() 
import os
import re

app = Flask(__name__)
sslify = SSLify(app)

#new  db
uri = os.environ.get('DATABASE_URL')  # or other relevant config var
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


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
    ppg3= Column(Float)
    ppm3= Column(Float)
    pp90_3= Column(Float)
    vpm90_3= Column(Float)
    ppg6= Column(Float)
    ppm6= Column(Float)
    pp90_6= Column(Float)
    vpm90_6= Column(Float)
    ppg10= Column(Float)
    ppm10= Column(Float)
    pp90_10= Column(Float)
    vpm90_10= Column(Float)


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

def create_tables():
    db.create_all()

@app.route("/")
@app.route("/home")
def home_page():
    return render_template('home.html')

@app.route('/about/<username>')
def about_page(username):
    return f'<h1>This is the about page of {username}</h1>'

@app.route('/players-overview', methods=['POST','GET'])
def all_players():
    season_started = True
    fpl_json = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/').json()
    events_df = pd.DataFrame(fpl_json['events'])
    if math.isnan(events_df.iloc[0].most_captained) == True:
        season_started = False
    latest_gw = events_df.dropna(subset=['most_captained']).iloc[-1].id

    minutes_threshold = 0.2*90*latest_gw
    players = Player.query.filter(Player.minutes >= minutes_threshold).all()
    command = request.form.get('please_show')
    if command == 'yes':
        players = Player.query.all()
    
    return render_template('players-overview.html', players=players, command=command, season_started=season_started)

@app.route('/player_comparison', methods=['POST'])
def player_comparison():
    players = Player.query.all()
    season_started = True
    fpl_json = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/').json()
    events_df = pd.DataFrame(fpl_json['events'])
    if math.isnan(events_df.iloc[0].most_captained) == True:
        season_started = False
    latest_gw = events_df.dropna(subset=['most_captained']).iloc[-1].id
    

    maxwk = request.form.get('maxwk')
    minwk = request.form.get('minwk')
  
    if maxwk < minwk:
        error_statement = "Initial gameweek value must be lower than final gameweek value"
   
        return render_template("comp_form.html", error_statement = error_statement, players=players, latest_gw=latest_gw, season_started= season_started)
    

    selected_players = request.form.getlist('selected_players')
  
    if len(selected_players)==0:
        player_select_error = "At least one player must be selected"
        return render_template("comp_form.html", player_select_error = player_select_error, players=players, latest_gw=latest_gw, season_started= season_started)
    df = pd.read_sql_query(
    sql = db.session.query(t_record.c.first_name, 
                        t_record.c.second_name,t_record.c.round,t_record.c.VPM90).filter(t_record.c.element.in_(selected_players), t_record.c.round>= minwk, t_record.c.round <= maxwk).statement,
    con = db.engine)
    df['name'] = df['first_name'] + ' ' + df['second_name']
    fig = px.line(df, x="round", y="VPM90", color='name', title = f"Player Comparison (GW{minwk}-{maxwk})", labels={
        "round": "Gameweek"
    })
    fig.update_xaxes(tick0=minwk, dtick=1)
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    compared_players = Player.query.filter(Player.id.in_(selected_players)).all()
    return render_template('comparison.html',graphJSON=graphJSON, selected_players=selected_players, compared_players=compared_players)

@app.route('/player_comp_form')
def comp_form():
    players = Player.query.all()
    season_started = True
    fpl_json = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/').json()
    events_df = pd.DataFrame(fpl_json['events'])
    if math.isnan(events_df.iloc[0].most_captained) == True:
        season_started = False
    latest_gw = events_df.dropna(subset=['most_captained']).iloc[-1].id
    return render_template('comp_form.html', players=players, latest_gw=latest_gw, season_started= season_started)

@app.route('/my_players', methods=['POST','GET'])
def my_players():
    season_started = True
    fpl_json = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/').json()
    events_df = pd.DataFrame(fpl_json['events'])
    if math.isnan(events_df.iloc[0].most_captained) == True:
        season_started = False
    latest_gw = events_df.dropna(subset=['most_captained']).iloc[-1].id

    if request.method== 'POST':
        team_id = request.form.get('team_id')
        team_url = f'https://fantasy.premierleague.com/api/entry/{team_id}/event/{latest_gw}/picks/'
        team_json = requests.get(team_url).json()
        try:
            team_df = pd.DataFrame(team_json['picks'])
            picks = list(team_df.element)
            name_url = f'https://fantasy.premierleague.com/api/entry/{team_id}/'
            name_json = requests.get(name_url).json()
            team_name = name_json['name']

            df = pd.read_sql_query(
            sql = db.session.query(t_record.c.first_name, 
                                t_record.c.second_name,t_record.c.round,t_record.c.VPM90).filter(t_record.c.element.in_(picks)).statement,
            con = db.engine)
            df['name'] = df['first_name'] + ' ' + df['second_name']
            fig = px.line(df, x="round", y="VPM90", color='name', title = f"{team_name} VPM90 Overview", labels={
                "round": "Gameweek"
            })
            fig.update_xaxes(tick0=1, dtick=1)
            graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            return render_template('my_players.html', team_id=team_id, season_started=season_started, latest_gw=latest_gw, graphJSON=graphJSON)
        except:
            error_msg = 'Please enter a valid team ID.'
            return render_template('my_players.html', error_msg=error_msg)
    return render_template('my_players.html',season_started=season_started, latest_gw=latest_gw)



@app.route('/player/<playerid>')
def player_page(playerid):
    this_player = db.session.query(t_record).filter(t_record.c.element== playerid).all()
    return render_template('player_profile.html',this_player=this_player)

@app.route('/methodology')
def method_page():
    lowest_gkp = Player.query.filter(Player.position=='GKP').order_by(Player.now_cost).first()
    lowest_def = Player.query.filter(Player.position=='DEF').order_by(Player.now_cost).first()
    lowest_mid = Player.query.filter(Player.position=='MID').order_by(Player.now_cost).first()
    lowest_fwd = Player.query.filter(Player.position=='FWD').order_by(Player.now_cost).first()
    return render_template('methodology.html',lowest_gkp=lowest_gkp, lowest_def=lowest_def,lowest_mid=lowest_mid,lowest_fwd=lowest_fwd)

if __name__ == '__main__':
    app.run(debug=True) 