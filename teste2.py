from functions import prepare_data, get_bar_info, init_func, frame_generator, anim_func
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from PIL import Image
from matplotlib.colors import ListedColormap
from matplotlib.animation import FuncAnimation
import bar_chart_race as bcr

today_date = datetime.today().strftime("%Y-%m-%d")
query = f"""
SELECT DATE(date_match) AS date_match, country_name, league_name, home_team, away_team,
betsresult, selection, leagues.api_id AS league_id,
away_team.api_id AS away_api_id, home_team.api_id AS home_api_id,
CONCAT("https://assets.b365api.com/images/team/b/", away_team.image_id, ".png") AS away_image,
CONCAT("https://assets.b365api.com/images/team/b/", home_team.image_id, ".png") AS home_image
FROM fellabot_bets
LEFT JOIN leagues ON fellabot_bets.league_name = leagues.name
LEFT JOIN teams AS home_team ON fellabot_bets.home_team = home_team.name
LEFT JOIN teams AS away_team ON fellabot_bets.away_team = away_team.name
WHERE date_match >= "2024-01-01" AND  date_match  <= "{today_date}" AND leagues.api_id IN (155)
ORDER BY date_match ASC
"""

DB_CONNECTION = "mysql+pymysql://soccer:545Kq&gxkTZVpSreeV8xzHzvRnst&&Z3@34.196.32.157:3306/soccer"
engine = create_engine(DB_CONNECTION)
connection = engine.connect()

df = pd.read_sql_query(query, con=connection)
teams_list = pd.concat([df["home_team"], df["away_team"]]).unique()
# Verifica para cada time quando a aposta foi feita nele como mandante (H) ou visitante (A)
list_dfs = []
for team in teams_list:
    df_team = df.query(f"(away_team == '{team}' and selection == 'A') or (home_team == '{team}' and selection == 'H')")
    cumsum = df_team.sort_values(by="date_match")["betsresult"].cumsum()
    df_team = df_team.assign(result_cumsum=cumsum, team=team)
    list_dfs.append(df_team)
final_df = pd.concat(list_dfs, axis=0).sort_values(by="date_match").reset_index(drop=True)
final_df = final_df[['date_match', 'team', 'result_cumsum']]
min_date = final_df["date_match"].min()
max_date = final_df["date_match"].max()
initial_date = final_df["date_match"].min() - timedelta(days=1)
date_generated = [initial_date + timedelta(days=x) for x in range(0, (max_date-initial_date).days)]
other_days_df_list = []
for d in date_generated:
    if d not in final_df["date_match"].values:
        date_col_list = [d] * len(teams_list)
        cumsum_col_list = [np.nan] * len(teams_list)
        other_days_df = pd.DataFrame({"date_match": date_col_list, "team": teams_list, "result_cumsum": cumsum_col_list})
        other_days_df_list.append(other_days_df)

df_days_off = pd.concat(other_days_df_list, axis=0)
final_df = pd.concat([final_df, df_days_off], axis=0).sort_values(by="date_match")
final_df_pivot = final_df.pivot(index='date_match', columns='team', values='result_cumsum').ffill().fillna(0) * 100
final_df_pivot.index = pd.to_datetime(final_df_pivot.index)

df_values, df_ranks = prepare_data(final_df_pivot)
fig, ax = plt.subplots(figsize=(16, 9))
title = "Lucros e prejuízos apostando R$ 100,00 Brasileirão 2024"
period_length = 2000
steps_per_period = 10
end_period_pause = 1000
n_bars = 20
filename = "teste.mp4"
fps = 30
writer = plt.rcParams['animation.writer']

interval = period_length / steps_per_period
pause = int(end_period_pause // interval)
frames = frame_generator(len(df_values), pause, steps_per_period)


anim = FuncAnimation(fig, anim_func, frames, init_func, interval=interval,
                     fargs=(fig, title, df_values, df_ranks, n_bars))
anim.save(filename, fps=fps, writer=writer) 