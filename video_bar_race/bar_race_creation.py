import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)
from bar_chart_race._bar_chart_race import bar_chart_race

from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.editor import VideoFileClip, concatenate_videoclips, concatenate_audioclips

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from PIL import Image
from matplotlib.colors import ListedColormap
from matplotlib.font_manager import FontProperties

bar_chart_race_path = "/mnt/wsl/PHYSICALDRIVE1/bar_chart_race/video_bar_race/"

def get_data():
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
    final_df = final_df[["date_match", "team", "result_cumsum"]]
    min_date = final_df["date_match"].min()
    max_date = final_df["date_match"].max()
    initial_date = final_df["date_match"].min() - timedelta(days=2)
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
    final_df_pivot = final_df.pivot(index="date_match", columns="team", values="result_cumsum").ffill().fillna(0) * 100
    final_df_pivot.index = pd.to_datetime(final_df_pivot.index)
    return final_df_pivot

def create_bar_race(title, final_df_pivot, filename=None):
    custom_font = FontProperties(fname=f"{bar_chart_race_path}resources/Montserrat-Regular.ttf")

    max_value = int(final_df_pivot.abs().max().max())
    img = np.asarray(Image.open(f"{bar_chart_race_path}resources/background.png"))
    fig, ax = plt.subplots(figsize=(16, 9))
    for label in ax.get_xticklabels():
        label.set_fontproperties(custom_font)
    for label in ax.get_yticklabels():
        label.set_fontproperties(custom_font)

    max_value = int(final_df_pivot.abs().max().max())
    ax.set_xlim(-max_value-100, max_value+100)
    ax.set_title(title, size=22, weight="bold", fontproperties=custom_font)
    for edge in ["top", "bottom", "left", "right"]:
        ax.spines[edge].set_visible(False)
    ax.tick_params(left=False)
    ax.get_xaxis().set_visible(False)
    ax.tick_params(axis="y", labelsize=12)
    ax.set_facecolor("none")

    background_ax = plt.axes([0, 0, 1, 1])
    background_ax.set_zorder(-1)
    background_ax.imshow(img, aspect="auto")
    for edge in ["top", "bottom", "left", "right"]:
        background_ax.spines[edge].set_visible(False)
    background_ax.tick_params(left=False)
    background_ax.get_xaxis().set_visible(False)
    background_ax.get_yaxis().set_visible(False)

    df_images = pd.read_csv(f"{bar_chart_race_path}resources/df_images.csv")
    colors = dict(zip(df_images["team"], df_images["color"]))
    custom_cmap = ListedColormap([colors[col] for col in final_df_pivot.columns])

    bar_chart_race(
        fig=fig,
        df=final_df_pivot,
        filename=f"{bar_chart_race_path}video/{filename}",
        orientation="h",
        sort="desc",
        n_bars=20,
        fixed_order=False,
        fixed_max=True,
        steps_per_period=10,
        period_length=2000,
        end_period_pause=2000,
        interpolate_period=False,
        bar_size=1,
        bar_textposition="outside",
        period_label={"x": 1.1, "y": .25, "ha": "right", "va": "center", "size": 40,
                      "color": "grey", "ha": "right", "weight": "bold", "fontproperties": custom_font},
        period_template="%d/%m/%Y",
        colors=custom_cmap,
        scale="linear",
        writer=None,
        bar_kwargs={"alpha": .7},
        bar_label_font=12,
        tick_label_font=12)

def add_song(input_filename, output_filename):
    freeze_duration = 10
    video_clip = VideoFileClip(f"{bar_chart_race_path}video/{input_filename}")
    video_clip_duration = video_clip.duration
    last_frame = video_clip.subclip(video_clip_duration - 0.2, video_clip_duration)
    freeze_frame = last_frame.set_duration(freeze_duration)
    
    audio_clip = CompositeAudioClip([AudioFileClip(f"{bar_chart_race_path}resources/AXIS1203_01_Be You_Full.mp3")])
    audio_clip_duration = audio_clip.duration
    if audio_clip_duration < video_clip_duration + freeze_duration:
        final_audio_clip = concatenate_audioclips([audio_clip, audio_clip])
    else:
        final_audio_clip = audio_clip
    final_audio_clip = final_audio_clip.subclip(0, video_clip_duration + freeze_duration)
    final_audio_clip = final_audio_clip.audio_fadeout(5)

    video_clip.audio = final_audio_clip
    final_video_clip = concatenate_videoclips([video_clip, freeze_frame])
    final_video_clip.write_videofile(f"{bar_chart_race_path}video/{output_filename}")

if __name__ == "__main__":
    final_df_pivot = get_data()
    title = "Lucros e prejuízos apostando R$ 100,00 no Brasileirão 2024"
    input_filename = "bar_race_output_no_audio.mp4"
    output_filename = "bar_race_output_video.mp4"
    create_bar_race(title, final_df_pivot, input_filename)
    add_song(input_filename, output_filename)