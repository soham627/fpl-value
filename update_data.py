from unicodedata import decimal
from attr import asdict
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

player_overview_df = elements_df[['id','first_name','second_name','team','element_type','points_per_game','total_points','minutes','now_cost', 'expected_goals','expected_assists','expected_goal_involvements']]
player_overview_df['position'] = player_overview_df.element_type.map(elements_types_df.set_index('id').singular_name_short)
player_overview_df['team'] = player_overview_df.team.map(teams_df.set_index('id').name)
player_overview_df['now_cost']=player_overview_df['now_cost']/10
player_overview_df['expected_goals'] = player_overview_df['expected_goals'].apply(lambda x: float(x)).round(decimals=2)
player_overview_df['expected_assists'] = player_overview_df['expected_assists'].apply(lambda x: float(x)).round(decimals=2)
player_overview_df['expected_goal_involvements'] = player_overview_df['expected_goal_involvements'].apply(lambda x: float(x)).round(decimals=1)

player_overview_df['points_per_90']= (player_overview_df['total_points']*90/player_overview_df['minutes']).round(decimals=1)
player_overview_df['points_per_mil'] = (player_overview_df['total_points']/player_overview_df['now_cost']).round(decimals=1)

##rearranging columns for readability
player_overview_df = player_overview_df.drop(['element_type'], axis=1)
column_names = ['id','first_name','second_name','team','position','points_per_game','total_points','minutes','now_cost',
            'points_per_90','points_per_mil','expected_goals','expected_assists','expected_goal_involvements']
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
latest_vpm90_df = pd.DataFrame(columns=['element','VPM90'])
last_3_df= pd.DataFrame(columns=['element_3','ppg3','ppm3','pp90_3','vpm90_3','pts3','min3', 'xg3','xa3','xgi3'])
last_6_df= pd.DataFrame(columns=['element_6','ppg6','ppm6','pp90_6','vpm90_6','pts6','min6','xg6','xa6','xgi6'])
last_10_df= pd.DataFrame(columns=['element_10','ppg10','ppm10','pp90_10','vpm90_10','pts10','min10','xg10','xa10','xgi10'])

for i in players_who_played.id:
    url = 'https://fantasy.premierleague.com/api/element-summary/{playerid}/'.format(playerid = i)
    r = requests.get(url)
    p_json = r.json()
    player_df = pd.DataFrame(p_json['history'])
    player_df['value'] = player_df['value']/10
    player_df['VPM90']= calculate_vpm90(player_df)
    player_df['VPM90']= player_df['VPM90'].round(decimals=1)
    latest_vpm90_df.loc[len(latest_vpm90_df)] = {'element': player_df['element'].iloc[-1], 'VPM90': player_df['VPM90'].iloc[-1]}

    def last_x_stats(n,df,pl_df):

        last_x = pl_df[['element','total_points','minutes','value', 'expected_goals',
        'expected_assists','expected_goal_involvements']].tail(n).reset_index()

        last_x[f'VPM90_{n}'] = calculate_vpm90(last_x)
        last_x['expected_goals'] = last_x['expected_goals'].apply(lambda x: float(x)).round(decimals=2)
        last_x['expected_assists'] = last_x['expected_assists'].apply(lambda x: float(x)).round(decimals=2)
        last_x['expected_goal_involvements'] = last_x['expected_goal_involvements'].apply(lambda x: float(x)).round(decimals=1)
        vpm90_x = round(last_x[f'VPM90_{n}'].iloc[-1],1)
        if last_x['minutes'].sum() == 0:
            ppgx = 0
            ppmx = 0
            pp90_x = 0
        else:
            ppgx = round(last_x['total_points'].sum()/last_x['minutes'].gt(0).sum(),1)
            ppmx = round(((1/n)* last_x['total_points']/last_x['value']).sum(),1)
            pp90_x = round(last_x['total_points'].sum()*90/last_x['minutes'].sum(),1)
        p_element = last_x['element'].iloc[0]
        min_x = last_x['minutes'].sum()
        pts_x = last_x['total_points'].sum()
        xg_x = last_x['expected_goals'].sum().round(decimals=2)
        xa_x = last_x['expected_assists'].sum().round(decimals=2)
        xgi_x = last_x['expected_goal_involvements'].sum().round(decimals=1)
        entry_to_add = [p_element, ppgx, ppmx, pp90_x, vpm90_x,pts_x, min_x, xg_x, xa_x,xgi_x]
        df.loc[len(df)] = entry_to_add
        return df
    
    last_3_df = last_x_stats(3,last_3_df,player_df)
    last_6_df = last_x_stats(6,last_6_df,player_df)
    last_10_df = last_x_stats(10,last_10_df,player_df)
    

        


    player_df['first_name'] = player_df.element.map(elements_df.set_index('id').first_name)
    player_df['second_name'] = player_df.element.map(elements_df.set_index('id').second_name)
    focused_df = player_df[['first_name', 'second_name','element', 'fixture', 'opponent_team', 'total_points', 'was_home', 'kickoff_time', 'round', 'minutes','goals_scored', 'assists','value','VPM90', 
    'expected_goals','expected_assists','expected_goal_involvements']]
    player_records_df = pd.concat([player_records_df,focused_df],ignore_index=True)
    
## creating id for primary key
player_records_df['id'] = player_records_df.index+1

player_overview_df = pd.merge(player_overview_df,latest_vpm90_df,left_on='id', right_on ='element')

player_overview_df = pd.merge(player_overview_df,last_3_df,left_on='id', right_on ='element_3')
player_overview_df = pd.merge(player_overview_df,last_6_df,left_on='id', right_on ='element_6')
player_overview_df = pd.merge(player_overview_df,last_10_df,left_on='id', right_on ='element_10')

##commenting out 2021-22 teams table since already created 
""" teams_2122 = teams_df[['id','name']]

teams_2122.to_sql(name='team2122',con=db.engine, index=False, if_exists='replace',dtype={
    'id': Integer,
    'name': Text
}) """

#COMMENT OUT AFTER FIRST RUN 
"""teams_2223 = teams_df[['id','name']]

teams_2223.to_sql(name='team2223',con=db.engine, index=False, if_exists='replace',dtype={
    'id': Integer,
    'name': Text
}) """

#COMMENT OUT AFTER FIRST RUN 
"""teams_2324 = teams_df[['id','name']]

teams_2324.to_sql(name='team2324',con=db.engine, index=False, if_exists='replace',dtype={
    'id': Integer,
    'name': Text
}) """


con = sqlalchemy.create_engine(uri, encoding='utf8')
## removing the foreign key constraints after the tables already exist so that they can be dropped and replaced

## COMMENT THIS BACK IN AFTER FIRST RUN 
con.execute('alter table record drop constraint teamer')
con.execute('alter table record drop constraint player_connect')

### saving tables from 21-22 season - COMMENT THIS OUT AFTER FIRST RUN

#con.execute('create table a_player_2122 AS TABLE player')

#con.execute('create table a_record_2122 AS TABLE record')

### saving tables from 22-23 season - COMMENT THIS OUT AFTER FIRST RUN
#con.execute('create table a_player_2223 AS TABLE player')
#con.execute('create table a_record_2223 AS TABLE record')


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
    'VPM90': Float,
    'expected_goals': Float,
    'expected_assists': Float,
    'expected_goal_involvements': Float,
    'ppg3': Float,
    'ppm3': Float,
    'pp90_3': Float,
    'vpm90_3': Float,
    'pts3': Integer,
    'min3': Integer,
    'xg3': Float,
    'xa3': Float,
    'xgi3': Float,
    'ppg6': Float,
    'ppm6': Float,
    'pp90_6': Float,
    'vpm90_6': Float,
    'pts6': Integer,
    'min6': Integer,
    'xg6': Float,
    'xa6': Float,
    'xgi6': Float,
    'ppg10': Float,
    'ppm10': Float,
    'pp90_10': Float,
    'vpm90_10': Float,
    'pts10': Integer,
    'min10': Integer,
    'xg10': Float,
    'xa10': Float,
    'xgi10': Float
})

player_records_df.to_sql(name = 'record',con=db.engine, index=False,if_exists='replace', dtype={
    'id': Integer,
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
    'VPM90': Float,
    'expected_goals': Float,
    'expected_assists': Float,
    'expected_goal_involvements': Float

})

con.execute('alter table player add primary key(id)')


## Comment out after first run
#con.execute('alter table team2122 add primary key(id)')
#con.execute('alter table team2223 add primary key(id)')
#con.execute('alter table team2324 add primary key(id)')


con.execute('alter table record add primary key(id)')
#Change the reference year here before the new season
con.execute('alter table record add constraint teamer foreign key (opponent_team) references team2324(id)')
con.execute('alter table record add constraint player_connect foreign key (element) references player(id)')

## for future years 
##create new teams table and then comment out after first run
## comment out the 'drop constraints' until after the first run, then comment them in'
## comment out the code that saves the last season's tables to the archive
## comment out team table adding primary key after first run 