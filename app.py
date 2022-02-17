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
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, Table, Text
from sqlalchemy.orm import relationship
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
    pts3= Column(Integer)
    min3= Column(Integer)
    ppg6= Column(Float)
    ppm6= Column(Float)
    pp90_6= Column(Float)
    vpm90_6= Column(Float)
    pts6= Column(Integer)
    min6= Column(Integer)
    ppg10= Column(Float)
    ppm10= Column(Float)
    pp90_10= Column(Float)
    vpm90_10= Column(Float)
    pts10= Column(Integer)
    min10= Column(Integer)
    player_records = relationship("Record", backref= "player")



class Team(Base):
    __tablename__ = 'team2122'
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    records = relationship("Record", backref= "oppteam")


class Record(Base):
    __tablename__ = 'record'

    id = Column(Integer, primary_key=True)
    first_name = Column(Text)
    second_name = Column(Text)
    element = Column(Integer, ForeignKey('player.id'))
    fixture = Column(Integer)
    opponent_team = Column(Integer, ForeignKey('team2122.id'))
    total_points = Column(Integer)
    was_home = Column(Boolean)
    kickoff_time = Column(Text)
    round = Column(Integer)
    minutes = Column(Integer)
    goals_scored = Column(Integer)
    assists = Column(Integer)
    value = Column(Float)
    VPM90 = Column(Float)
   

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
    show_last = request.form.get('week_filter')

    if show_last== 'a':
        minutes_threshold = 90
        players = Player.query.filter(Player.min3 >= minutes_threshold).all()
    elif show_last == 'b':
        minutes_threshold = 270
        players = Player.query.filter(Player.min6 >= minutes_threshold).all()
    elif show_last == 'c':
        minutes_threshold = 450
        players = Player.query.filter(Player.min10 >= minutes_threshold).all()
    else:
        minutes_threshold = 0.2*90*latest_gw
        players = Player.query.filter(Player.minutes >= minutes_threshold).all()
    command = request.form.get('please_show')
    if command == 'yes':
        players = Player.query.all()

    
    return render_template('players-overview.html', players=players, command=command, season_started=season_started, show_last=show_last)

@app.route('/player_comparison', methods=['POST'])
def player_comparison():
    players = Player.query.all()
    season_started = True
    fpl_json = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/').json()
    events_df = pd.DataFrame(fpl_json['events'])
    if math.isnan(events_df.iloc[0].most_captained) == True:
        season_started = False
    latest_gw = events_df.dropna(subset=['most_captained']).iloc[-1].id
    

    maxwk = int(request.form.get('maxwk'))
    minwk = int(request.form.get('minwk'))
  
    if maxwk < minwk:
        error_statement = "Initial gameweek value must be lower than final gameweek value"
   
        return render_template("comp_form.html", error_statement = error_statement, players=players, latest_gw=latest_gw, season_started= season_started)
    

    selected_players = request.form.getlist('selected_players')
  
    if len(selected_players)==0:
        player_select_error = "At least one player must be selected"
        return render_template("comp_form.html", player_select_error = player_select_error, players=players, latest_gw=latest_gw, season_started= season_started)
    df = pd.read_sql_query(
    sql = db.session.query(Record.first_name, 
                        Record.second_name,Record.round,Record.VPM90).filter(Record.element.in_(selected_players), Record.round>= minwk, Record.round <= maxwk).statement,
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

@app.route('/regret')
def regret():
    players = Player.query.all()
    return render_template('regret.html', players=players)

@app.route('/regret_results',methods=['POST'])
def regret_results():
    und_player = int(request.form.get('und_player'))
    the_player = Player.query.filter(Player.id == und_player).first()
    num_weeks = request.form.get('week')
    if num_weeks == 'full':
        better_players = Player.query.filter(Player.total_points> the_player.total_points, Player.position == the_player.position, Player.points_per_mil>the_player.points_per_mil, Player.now_cost <= the_player.now_cost)
    elif num_weeks == '3':
        better_players = Player.query.filter(Player.pts3> the_player.pts3, Player.position == the_player.position, Player.ppm3>the_player.ppm3, Player.now_cost <= the_player.now_cost)
    elif num_weeks == '6':
        better_players = Player.query.filter(Player.pts6> the_player.pts6, Player.position == the_player.position, Player.ppm6>the_player.ppm6, Player.now_cost <= the_player.now_cost)
    elif num_weeks == '10':
        better_players = Player.query.filter(Player.pts10> the_player.pts10, Player.position == the_player.position, Player.ppm10>the_player.ppm10, Player.now_cost <= the_player.now_cost)
    return render_template('regret_results.html', the_player=the_player, num_weeks=num_weeks, better_players=better_players)


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
            sql = db.session.query(Record.first_name, 
                                Record.second_name,Record.round,Record.VPM90).filter(Record.element.in_(picks)).statement,
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
    this_player = Record.query.filter(Record.element== playerid).all()
    return render_template('player_profile.html',this_player=this_player)

@app.route('/methodology')
def method_page():
    lowest_gkp = Player.query.filter(Player.position=='GKP').order_by(Player.now_cost).first()
    lowest_def = Player.query.filter(Player.position=='DEF').order_by(Player.now_cost).first()
    lowest_mid = Player.query.filter(Player.position=='MID').order_by(Player.now_cost).first()
    lowest_fwd = Player.query.filter(Player.position=='FWD').order_by(Player.now_cost).first()
    return render_template('methodology.html',lowest_gkp=lowest_gkp, lowest_def=lowest_def,lowest_mid=lowest_mid,lowest_fwd=lowest_fwd)

@app.route('/insights')
def insights_page():
    return render_template('insights.html')

if __name__ == '__main__':
    app.run(debug=True) 