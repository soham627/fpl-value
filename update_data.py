from pandas.io.formats.format import TextAdjustment
from sqlalchemy.sql.sqltypes import Boolean, Float
from app import db
import requests 
import pandas as pd
pd.options.mode.chained_assignment = None 
from sqlalchemy.types import Integer, Text, String, DateTime
import sqlalchemy
import os 
import re

uri = os.environ.get('DATABASE_URL')  
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
r = requests.get(url)
json = r.json()

elements_df = pd.DataFrame(json['elements'])
elements_types_df = pd.DataFrame(json['element_types'])
teams_df = pd.DataFrame(json['teams'])

player_overview_df = elements_df[['id','first_name','second_name','team','element_type','points_per_game','total_points','minutes','now_cost']]
player_overview_df['position'] = player_overview_df.element_type.map(elements_types_df.set_index('id').singular_name_short)
player_overview_df['team'] = player_overview_df.team.map(teams_df.set_index('id').name)
player_overview_df['now_cost']=player_overview_df['now_cost']/10


player_overview_df['points_per_90']= (player_overview_df['total_points']*90/player_overview_df['minutes']).round(decimals=1)
player_overview_df['points_per_mil'] = (player_overview_df['total_points']/player_overview_df['now_cost']).round(decimals=1)

##rearranging columns for readability
player_overview_df = player_overview_df.drop(['element_type'], axis=1)
column_names = ['id','first_name','second_name','team','position','points_per_game','total_points','minutes','now_cost',
            'points_per_90','points_per_mil']
player_overview_df = player_overview_df.reindex(columns=column_names)

def calculate_vpm90(df):
    
    ## Adjusting player value (reducing GK/DEF/FWD value by 4.0, and MID by 4.5 since that is the lowest you can spend on a player of that position)
    json = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/').json()
    elements_df = pd.DataFrame(json['elements'])
    
    ## calculating the vpm90
    cumul_mins = 0
    weighted_vpm90_list = []
    this_wk_vpm90_list = []

    ## finding the lowest priced players at each position
    mp_gkp = player_overview_df.loc[player_overview_df.position=='GKP'].now_cost.min()
    mp_def = player_overview_df.loc[player_overview_df.position=='DEF'].now_cost.min()
    mp_mid = player_overview_df.loc[player_overview_df.position=='MID'].now_cost.min()
    mp_fwd = player_overview_df.loc[player_overview_df.position=='FWD'].now_cost.min()
    ## checking the player's position and calculating the adjusted player price accordingly
    if elements_df.loc[elements_df.id==df['element'][0]].iloc[0].element_type ==1:
        min_price = mp_gkp
    elif elements_df.loc[elements_df.id==df['element'][0]].iloc[0].element_type ==2:
        min_price = mp_def
    elif elements_df.loc[elements_df.id==df['element'][0]].iloc[0].element_type ==3:
        min_price = mp_mid
    elif elements_df.loc[elements_df.id==df['element'][0]].iloc[0].element_type ==4:
        min_price = mp_fwd
    
    for i in range(len(df)):
        cumul_mins = cumul_mins + df.loc[i,'minutes']
        ## if no minutes were played, the previous value of vpm90 will be used - as the value per minute played has not changed
        if df.loc[i,'minutes']==0:
            this_wk_vpm90_list.append(0)
            if i==0:
                weighted_vpm90_list.append(0)
            else:
                weighted_vpm90_list.append(weighted_vpm90_list[i-1])
        ## if minutes were played, calculate the current week's vpm90 and then use all the previous vpm90's 
        else:
            ## calculates vpm90 for the current gameweek
            this_wk_val = (df.loc[i,'total_points']/(max(df.loc[i,'value']-min_price,0.1))*90/df.loc[i,'minutes'])
            this_wk_vpm90_list.append(this_wk_val)
            ## if this is gameweek 1, the current gameweek's vpm90 is appended to the cumulative vp90 list
            if i == 0:
                weighted_vpm90_list.append(this_wk_val)
            ## after GW1, the this_wk_vpn90 values from previous weeks are used to create a weighted average vpn90
            else:
                weighted_vpm90 = this_wk_val*(df.loc[i,'minutes']/cumul_mins)
                for j in range(i):
                    weighted_vpm90 = weighted_vpm90 + (this_wk_vpm90_list[j]*df.loc[j,'minutes']/cumul_mins)
                weighted_vpm90_list.append(weighted_vpm90)
    return weighted_vpm90_list

players_who_played = elements_df.loc[elements_df.minutes>0]
player_records_df = pd.DataFrame()
latest_vpm90_df = pd.DataFrame()
for i in players_who_played.id:
    url = 'https://fantasy.premierleague.com/api/element-summary/{playerid}/'.format(playerid = i)
    r = requests.get(url)
    json = r.json()
    player_df = pd.DataFrame(json['history'])
    player_df['value'] = player_df['value']/10
    player_df['VPM90']= calculate_vpm90(player_df)
    player_df['VPM90']= player_df['VPM90'].round(decimals=1)
    latest_vpm90_df = latest_vpm90_df.append(player_df[['element','VPM90']].iloc[-1])
    player_df['first_name'] = player_df.element.map(elements_df.set_index('id').first_name)
    player_df['second_name'] = player_df.element.map(elements_df.set_index('id').second_name)
    focused_df = player_df[['first_name', 'second_name','element', 'fixture', 'opponent_team', 'total_points', 'was_home', 'kickoff_time', 'round', 'minutes','goals_scored', 'assists','value','VPM90']]
    player_records_df = player_records_df.append(focused_df,ignore_index=True)
    

player_overview_df = pd.merge(player_overview_df,latest_vpm90_df,left_on='id', right_on ='element')

player_overview_df.to_sql(name='player', con=db.engine, index=False, if_exists='replace', dtype={
    "id": Integer,
    'first_name': Text,
    'second_name': Text,
    'team': Text,
    'position': Text,
    'points_per_game': Float,
    'total_points': Integer,
    'minutes': Integer,
    'now_cost': Float,
    'points_per_90': Float,
    'points_per_mil': Float,
    'element': Integer,
    'VPM90': Float

})

player_records_df.to_sql(name = 'record',con=db.engine, index=False,if_exists='replace', dtype={
    'first_name': Text,
    'second_name': Text,
    'element': Integer,
    'fixture': Integer,
    'opponent_team': Integer,
    'total_points': Integer,
    'was_home': Boolean,
    'kickoff_time': Text,
    'round': Integer,
    'minutes': Integer,
    'goals_scored': Integer, 
    'assists': Integer,
    'value': Float,
    'VPM90': Float

})

con = sqlalchemy.create_engine(uri, encoding='utf8')
con.execute('alter table player add primary key(id)')