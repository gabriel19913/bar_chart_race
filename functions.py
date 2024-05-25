import matplotlib
matplotlib.use('Qt5Agg')

import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt
from PIL import Image

def get_bar_colors(df):
    df_images = pd.read_csv('/home/gabriel/Documentos/projects/bar_chart_race/data/df_images.csv')
    colors = dict(zip(df_images["team"], df_images["color"]))
    custom_cmap = ListedColormap([colors[col] for col in df.columns])
    bar_colors = custom_cmap(range(custom_cmap.N)).tolist()
    n = len(bar_colors)
    if df.shape[1] > n:
        bar_colors = bar_colors * (df.shape[1] // n + 1)
    bar_colors = np.array(bar_colors[:df.shape[1]])
    return bar_colors

def prepare_wide_data(df, orientation='h', sort='desc', n_bars=None, interpolate_period=False, 
                      steps_per_period=10, compute_ranks=True):
    if n_bars is None:
        n_bars = df.shape[1]

    df_values = df.reset_index()
    df_values.index = df_values.index * steps_per_period
    new_index = range(df_values.index[-1] + 1)
    df_values = df_values.reindex(new_index)
    if interpolate_period:
        if df_values.iloc[:, 0].dtype.kind == 'M':
            first, last = df_values.iloc[[0, -1], 0]
            dr = pd.date_range(first, last, periods=len(df_values))
            df_values.iloc[:, 0] = dr
        else:
            df_values.iloc[:, 0] = df_values.iloc[:, 0].interpolate()
    else:
        df_values.iloc[:, 0] = df_values.iloc[:, 0].fillna(method='ffill')
    
    df_values = df_values.set_index(df_values.columns[0])
    if compute_ranks:
        df_ranks = df_values.rank(axis=1, method='first', ascending=False).clip(upper=n_bars + 1)
        if (sort == 'desc' and orientation == 'h') or (sort == 'asc' and orientation == 'v'):
            df_ranks = n_bars + 1 - df_ranks
        df_ranks = df_ranks.interpolate()
    
    df_values = df_values.interpolate()
    if compute_ranks:
        return df_values, df_ranks
    return df_values

def prepare_data(df, fixed_order=True, steps_per_period=5, n_bars=20):
    orientation='h'
    sort='desc'
    interpolate_period=False
    if fixed_order is True:
        last_values = df.iloc[-1].sort_values(ascending=False)
        cols = last_values.iloc[:n_bars].index
        df = df[cols]
    elif isinstance(fixed_order, list):
        cols = fixed_order
        df = df[cols]
        n_bars = min(len(cols), n_bars)
        
    compute_ranks = fixed_order is False
    dfs = prepare_wide_data(df, orientation, sort, n_bars,
                            interpolate_period, steps_per_period, compute_ranks)
    if isinstance(dfs, tuple):
        df_values, df_ranks = dfs
    else:
        df_values = dfs

    if fixed_order:
        n = df_values.shape[1] + 1
        m = df_values.shape[0]
        rank_row = np.arange(1, n)
        if (sort == 'desc' and orientation == 'h') or \
            (sort == 'asc' and orientation == 'v'):
            rank_row = rank_row[::-1]
        
        ranks_arr = np.repeat(rank_row.reshape(1, -1), m, axis=0)
        df_ranks = pd.DataFrame(data=ranks_arr, columns=cols)

    return df_values, df_ranks

def get_bar_info(df_values, df_ranks, n_bars, i):
    bar_colors = get_bar_colors(df_values)
    bar_location = df_ranks.iloc[i].values
    top_filt = (bar_location > 0) & (bar_location < n_bars + 1)
    bar_location = bar_location[top_filt]
    bar_length = df_values.iloc[i].values[top_filt]
    cols = df_values.columns[top_filt]
    colors = bar_colors[top_filt]
    return bar_location, bar_length, cols, colors

def plot_bars(ax, title, df_values, df_ranks, n_bars, i):
    img = np.asarray(Image.open('/home/gabriel/Documentos/projects/bar_chart_race/data/background.png'))
    bar_location, bar_length, cols, colors = get_bar_info(df_values, df_ranks, n_bars, i)
    max_value = int(df_values.abs().max().max())
    bar_values = ax.barh(bar_location, bar_length, tick_label=cols, color=colors)
    ax.set_xlim(-max_value, max_value)
    ax.bar_label(bar_values, padding=5, fontsize=14)
    ax.tick_params(axis='y', labelsize=12)
    for edge in ["top", "bottom", "left", "right"]:
        ax.spines[edge].set_visible(False)
    ax.tick_params(left=False)
    ax.get_xaxis().set_visible(False)
    ax.set_title(title, size=22, weight="bold")
    ax.set_facecolor('none')
    
    background_ax = plt.axes([0, 0, 1, 1])
    background_ax.set_zorder(-1) 
    background_ax.imshow(img, aspect='auto')
    for edge in ["top", "bottom", "left", "right"]:
        background_ax.spines[edge].set_visible(False)
    background_ax.tick_params(left=False)
    background_ax.get_xaxis().set_visible(False)
    background_ax.get_yaxis().set_visible(False)
    
    ax.text(710, 2, df_values.iloc[i,:].name.date().strftime("%d/%m/%Y"), fontsize=30, color='grey', ha='right',
            weight="bold", va='center', bbox=dict(facecolor='#ebebeb', edgecolor='none', pad=10.0))

def init_func(title, df_values, df_ranks, n_bars, fig):
    ax = fig.axes[0]
    plot_bars(ax, title, df_values, df_ranks, n_bars, i=0)

def frame_generator(n, pause, steps_per_period):
    frames = []
    for i in range(n):
        frames.append(i)
        if pause and i % steps_per_period == 0 and i != 0 and i != n - 1:
            for _ in range(pause):
                frames.append(None)
    return frames

def anim_func(i, fig, title, df_values, df_ranks, n_bars):
    if i is None:
        return
    ax = fig.axes[0]
    for bar in ax.containers:
        bar.remove()
    for text in ax.texts[0:]:
        text.remove()
    plot_bars(ax, title, df_values, df_ranks, n_bars, i)
