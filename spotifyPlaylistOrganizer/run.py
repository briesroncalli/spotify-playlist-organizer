# import necessary modules
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, url_for, session, redirect, render_template, json
import atexit
import os

# initialize Flask app
app = Flask(__name__)
app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie' # set the name of the session cookie
app.secret_key = 'YOUR_SECRET_KEY' # os.urandom(24) # set a random secret key to sign the cookie


# set the key for the token info in the session dictionary
TOKEN_INFO = 'token_info'

# home page
@app.route('/', methods=['GET', 'POST'])
def index():
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect(url_for('login', _external=False))
    clear_json_data()
    # get users playlists & saved albums
    playlist_dict, album_dict = get_user_playlists_albums()
    
    # get lists of playlists & albums for display
    playlists = [{'uri': uri, 
                  'name': playlist['name']}
                 for  uri, playlist in playlist_dict.items()]
    albums = [{'uri': uri, 
               'name': album['name'], 
               'artists': ", ".join([a['name'] for a in album['artists']])}
              for uri, album in album_dict.items()]
    
    # alphabetize lists of playlists & albums for display
    playlists = sorted(playlists, key=lambda x: x['name'])
    albums = sorted(albums, key=lambda x: x['name'])
    # submit form selections
    if request.method == 'POST':
        selected_playlist_uris = request.form.getlist('playlists[]')
        selected_album_uris = request.form.getlist('albums[]')
        selected_playlist_dict = {uri: playlist_dict[uri] for uri in selected_playlist_uris}
        selected_album_dict = {uri: album_dict[uri] for uri in selected_album_uris}
        songs = get_songs(selected_playlist_dict, selected_album_dict)
        with open('spotifyPlaylistOrganizer/data/songs.json', 'w') as f:
            json.dump(songs, f)
        print(f"Songs submitted: {len(songs)}")
        session['method'] = request.form.get('method')
        session['bounds'] = request.form.get('bounds')
        return redirect(url_for('sort_songs',_external=False))
        
    return render_template('index.html', playlists=playlists, albums=albums)

# route to handle logging in
@app.route('/login')
def login():
    # create a SpotifyOAuth instance and get the authorization URL
    auth_url = create_spotify_oauth().get_authorize_url()
    # redirect the user to the authorization URL
    return redirect(auth_url)

# route to handle the redirect URI after authorization
@app.route('/redirect')
def redirect_page():
    # clear the session
    session.clear()
    # get the authorization code from the request parameters
    code = request.args.get('code')
    # exchange the authorization code for an access token and refresh token
    token_info = create_spotify_oauth().get_access_token(code, as_dict=True)
    # save the token info in the session
    session[TOKEN_INFO] = token_info
    # redirect the user to the save_discover_weekly route
    return redirect(url_for('index',_external=False))

# runs the playlist organization
@app.route('/sortSongs')
def sort_songs():
    # get the clustering parameters
    metric = 'euclidean'
    method = session.get('method')
    bounds = [int(bound) for bound in session.get('bounds').split(",")]
    if len(bounds)==1:
        bounds.append(np.inf)
    try:
        with open('spotifyPlaylistOrganizer/data/songs.json', 'r') as f:
            song_data = json.load(f)
    except FileNotFoundError:
        return 'JSON data file not found.'
    song_uris = np.array(list(song_data.keys()))
    print(f"Songs retrieved: {len(song_uris)}")
    
    # create df of song audio features
    audio_features = get_audio_features(song_uris)
    comparison_cols = ['acousticness','danceability','energy','instrumentalness', 'loudness', 'valence']
    cols = comparison_cols + ['duration_ms']
    df = pd.DataFrame.from_dict(audio_features)
    df = df[cols]
    # normalize loudness between 0 and 1
    df['loudness'] /= 120
    df['loudness'] += 0.5
    
    # create clusters
    cluster_criterion = 'distance'
    labels = hierarchical_cluster(df[comparison_cols], method, metric, cluster_criterion, lower_bound=bounds[0], upper_bound=bounds[1], step_size=1.0)
    df.insert(0,'cluster', labels)
    clusters = []
    for label in np.unique(labels):
        clusters.append(song_uris[np.where(labels == label)])
    print(len(clusters), "clusters found")
    
    # find the averages by cluster
    playlist_avg_df = df[cols+['cluster']].groupby('cluster').mean()
    durations = playlist_avg_df['duration_ms'].apply(ms_to_mins_and_secs)
    
    # get 3 word descriptions of each playlist
    playlist_descriptions = get_playlist_description(playlist_avg_df[comparison_cols])
    
    # create radar plots of song data
    radar_chart_uris = playlist_radar_chart(playlist_avg_df[comparison_cols])
    
    # compute the popularity & plot
    popularities = []
    for cluster in clusters:
        popularities.append(np.mean([song_data[uri]['popularity']  for uri in cluster]))
    popularity_plot_uris = playlist_popularity_plot(popularities)
    
    return render_template('organized-playlists.html', cluster_list=clusters, song_data=song_data, playlist_descriptions=playlist_descriptions, radar_chart_uris=radar_chart_uris, popularity_plot_uris=popularity_plot_uris, durations=durations)

# gets the users saved playlists & albums
def get_user_playlists_albums():
    try: 
        # Get the token info from the session
        token_info = get_token()
    except:
        # If the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect(url_for('login', _external=False))
    
    # Create a Spotipy instance with the access token
    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    # Get the users playlists
    playlist_dict = dict()
    results = sp.current_user_playlists(limit=50)
    playlist_dict.update({playlist['uri']: playlist for playlist in results['items']})
    while results['next']:
        playlist_dict.update({playlist['uri']: playlist for playlist in results['items']})
    
    # Get the users albums
    album_dict = dict()
    results = sp.current_user_saved_albums(limit=50)
    album_dict.update({album['album']['uri']: album['album'] for album in results['items']})
    while results['next']:
        album_dict.update({album['album']['uri']: album['album'] for album in results['items']})
    return playlist_dict, album_dict

# get the uris for the songs in the selected playlists & albums
def get_songs(playlist_dict, album_dict):
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect(url_for('login', _external=False))
    
    # create a Spotipy instance with the access token
    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    song_data = {}
    # get songs from the selected albums
    for _, album in album_dict.items():
        prepped_album = {
            'name': album['name'],
            'external_urls': album['external_urls']['spotify'],
            'images': album['images'][-1]['url']
            }
        for song in album["tracks"]['items']:
            uri = song['uri']
            song = prep_song(song, album=True)
            song['album'] = prepped_album
            song_data[uri] = song
    
    # album songs do not list populatrity so must be retrieved separately
    if song_data:
        for uri, popularity in get_song_popularity(list(song_data.keys())).items():
            song_data[uri]['popularity'] = popularity
    
    # get songs from selected playlists
    for _, playlist in playlist_dict.items():
        results = sp.playlist_items(playlist['id'])
        for song in results['items']:
            uri = song['track']['uri']
            song_data[uri] = prep_song(song['track'], album=False)
        while results['next']:
            results = sp.next(results)
            for song in results['items']:
                uri = song['track']['uri']
                song_data[uri] = prep_song(song['track'], album=False)
    return song_data

def get_song_popularity(uris):
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect(url_for('login', _external=False))
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    popularities = {}
    batch_size = 50 # max 50 IDs
    num_batches = len(uris) // batch_size
    for i in range(0, num_batches):
        for song in sp.tracks(uris[i*batch_size:(i+1)*batch_size])['tracks']:
            popularities[song['uri']] = song['popularity']
    for song in sp.tracks(uris[num_batches*batch_size:])['tracks']:
        popularities[song['uri']] = song['popularity']
    return popularities

#  parses song data for get_songs_data()
def prep_song(song, album):
    song.pop('uri')
    song.pop('available_markets', None)
    song.pop('explicit', None)
    song.pop('track_number', None)
    song.pop('disc_number', None)
    song.pop('is_local', None)
    song.pop('external_ids', None)
    song.pop('type', None)
    song.pop('episode', None)
    song.pop('track', None)
    song.pop('href', None)
    song.pop('id', None)
    if not album:
        song['album'] = {
            'name': song['album']['name'],
            'external_urls': song['album']['external_urls']['spotify'],
            'images': song['album']['images'][-1]['url']
            }
    song['artists'] = [{'name': artist['name'], 'external_urls': artist['external_urls']['spotify']} for artist in song['artists']]
    song['external_urls'] = song['external_urls']['spotify']
    return song

# helper that converts song durations from ms (int) to '{minutes}:{seconds}' string
def ms_to_mins_and_secs(ms):
    total_seconds = ms / 1000
    return f"{int(total_seconds // 60)}:{int(total_seconds % 60):02d}"

# get the audio features for each song in song_uris
def get_audio_features(song_uris):
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect(url_for('login', _external=False))
    
    # create a Spotipy instance with the access token
    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    audio_features = []
    batch_size = 100
    num_batches = len(song_uris) // batch_size 
    for i in range(num_batches):
        audio_features += sp.audio_features(song_uris[i*batch_size:(i+1)*batch_size])
    audio_features += sp.audio_features(song_uris[num_batches*batch_size:])
    
    # check that got all songs' data
    if len(song_uris)-len(audio_features) != 0:
        print(f"WARNING: {len(song_uris)-len(audio_features)} songs missed!")
        
    return audio_features

# clusters the songs using hierarchical clustering
import numpy as np
from scipy.cluster import hierarchy
from scipy.cluster.hierarchy import fcluster
import pandas as pd
def hierarchical_cluster(df, method, metric, cluster_criterion, lower_bound, upper_bound, step_size=1.0):
    # make initial cluster estimation
    distance_threshold = 1.0
    linkage_matrix = hierarchy.linkage(df, method=method, metric=metric)
    labels = fcluster(linkage_matrix, t=distance_threshold, criterion=cluster_criterion)
    
    # ensure desired number of clusters w/ min length
    num_playlists = len(np.unique(labels))
    previous_num_playlists = -1
    min_songs_per_cluster = len(df) // upper_bound // 10
    if min_songs_per_cluster <= 1:
        min_songs_per_cluster = 2
    num_retries = 0
    print ("min_songs_per_cluster: ", min_songs_per_cluster)
    
    while num_playlists < lower_bound or num_playlists > upper_bound or min([np.count_nonzero(labels == label) for label in labels]) < min_songs_per_cluster:
        print('Retry clustering:', num_playlists)
        
        # if a cluster is too small, adjust step size & continue iteration
        if min([np.count_nonzero(labels == label) for label in labels]) < min_songs_per_cluster and previous_num_playlists != -1:
            if previous_num_playlists < num_playlists:
                distance_threshold += step_size
            else:
                distance_threshold -= step_size
            step_size /= 2
            num_retries += 1
        if num_retries > 10:
            break
        previous_num_playlists = num_playlists
        
        # if less clusters made than desired, decrease distance_threshold
        if num_playlists < lower_bound:
            distance_threshold -= step_size
        # if more clusters made than desired, increase distance_threshold
        elif num_playlists > upper_bound:
            distance_threshold += step_size

        # if jumped entire target range, reduce step size
        positive_overstep = previous_num_playlists < lower_bound and num_playlists > upper_bound
        negative_overstep = previous_num_playlists > upper_bound and num_playlists < lower_bound
        if positive_overstep or negative_overstep:
            step_size /= 2
            
        # reattempt clustering
        labels = fcluster(linkage_matrix, t=distance_threshold, criterion=cluster_criterion)
        num_playlists = len(np.unique(labels))
    
    return labels

# creates couple adjective description of playlists
def get_playlist_description(playlist_df):
    adjusted_df = abs(playlist_df - 0.5)
    num_cols = len(playlist_df.columns)
    descriptor_dict = { # category: [val<0.5, val>0.5]
        'acousticness': ['acoustic', 'electronic'],
        'danceability': ['dance', 'relax'],
        'energy': ['energetic', 'chill'],
        'instrumentalness': ['instrumental', 'vocal'],
        'loudness': ['loud', 'quiet'],
        'valence': ['happy', 'sad']
    }
    descriptors = []
    for idx, row in adjusted_df.iterrows():
        # generate 3 word descriptor
        num_adjectives = 3
        descriptor_list = []
        for category in row.nlargest(num_adjectives).index:
            is_negative = playlist_df[category].loc[idx] < 0.5
            descriptor_list.append(descriptor_dict[category][int(is_negative)])
        descriptor = ", ".join(descriptor_list)
        # check for pre-existing duplicate descriptor
        while descriptor in descriptors:
            num_adjectives += 1
            first_instance_idx = np.where(np.array(descriptors) ==  descriptor)[0][0]
            duplicate_row = adjusted_df.loc[first_instance_idx]
            
            # update current playlist descriptor
            descriptor_list = []
            for category in row.nlargest(num_adjectives).index:
                is_negative = playlist_df[category].loc[idx] < 0.5
                descriptor_list.append(descriptor_dict[category][int(is_negative)])
            descriptor = ", ".join(descriptor_list)
            
            # update current playlist descriptor
            duplicate_descriptor_list = []
            for category in duplicate_row.nlargest(num_adjectives).index:
                is_negative = playlist_df[category].loc[first_instance_idx] < 0.5
                duplicate_descriptor_list.append(descriptor_dict[category][int(is_negative)])
            descriptors[first_instance_idx] = ", ".join(duplicate_descriptor_list)
            
            # if columns all in same order, revert to only first 3
            if num_adjectives >= num_cols:
                num_adjectives = 3
                num_occurences = len(np.where(np.array(descriptors) ==  descriptor)[0]) + 1
                
                # reset current descriptor
                descriptor = []
                for category in row.nlargest(num_adjectives).index:
                    is_negative = playlist_df[category].loc[idx] < 0.5
                    descriptor_list.append(descriptor_dict[category][int(is_negative)])
                descriptor = ", ".join(descriptor) + f" {num_occurences}"
                
                # reset duplicate descriptor
                duplicate_descriptor = []
                for category in duplicate_row.nlargest(num_adjectives).index:
                    is_negative = playlist_df[category].loc[first_instance_idx] < 0.5
                    duplicate_descriptor.append(descriptor_dict[category][int(is_negative)])
                descriptors[first_instance_idx] = ", ".join(duplicate_descriptor)
                break
        descriptors.append(descriptor)
    
    return [d.capitalize() for d in descriptors]

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import matplotlib.font_manager as fm
def playlist_radar_chart(playlist_df, figsize=(8,8)):
    # set plot colors
    font_color = '#aaa'
    plot_color = '#1DB954'
    plot_color_highlight = '#25cf61'
    font = fm.FontProperties(family='sans-serif', size=26, weight='bold', style='oblique')
    
    cols = [col.capitalize() for col in playlist_df.columns]
    N = len(cols)
    plot_uris = []
    for idx in playlist_df.index:
        # create plot object & axes for radar plot
        fig = plt.figure(figsize=figsize)
        fig.patch.set_alpha(0.0)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]
        ax = plt.subplot(111, polar=True)
        ax.patch.set_alpha(0.0)
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.spines['polar'].set_visible(False)

        ax.set_xticks(angles[:-1], cols, fontproperties=font, color=font_color, horizontalalignment='center', verticalalignment='center')
        ax.tick_params(pad=30)
        plt.yticks([0.25,0.5,0.75,1.0],[])
        plt.ylim(0,1)
        
        # plot the playlist data (normal)
        values = list(playlist_df.loc[idx])
        values += values[:1]
        ax.plot(angles, values, linewidth=3, linestyle='solid', color=plot_color)
        ax.fill(angles, values, color=plot_color, alpha=0.3)
        plt.tight_layout()
        
        # save the normal plot
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        normal_plot_uri = base64.b64encode(buffer.read()).decode('utf8')
        buffer.close()

        # plot the playlist data (highlighted)
        values = list(playlist_df.loc[idx])
        values += values[:1]
        ax.plot(angles, values, linewidth=4, linestyle='solid', color=plot_color_highlight)
        ax.fill(angles, values, color=plot_color_highlight, alpha=0.2)
        plt.tight_layout()
        
        # save the highlighted plot
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        highlight_plot_uri = base64.b64encode(buffer.read()).decode('utf8')
        buffer.close()
        
        plot_uris.append([normal_plot_uri, highlight_plot_uri])
    
    return plot_uris

import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch
from matplotlib.patches import BoxStyle
def playlist_popularity_plot(popularities):
    fill_color = "#1DB954"
    grid_color = "#696969"
    fontcolor = "#aaa"
    background_color = "#181818"
    font = fm.FontProperties(family='sans-serif', size=26, weight='bold', style='oblique')
    fig_size = (3,9)
    popularity_plot_uris = []
    for popularity in popularities:
        fig = plt.figure(figsize=fig_size)
        fig.patch.set_alpha(0.0)
        ax = plt.subplot(111)
        ax.patch.set_alpha(0.0)
        ax.tick_params(pad=25, color=grid_color, width=2, length=10)
        ax = plt.bar(x=" ", width=1, height=popularity, color=fill_color)
        plt.tight_layout()
        new_patches = []
        p_bbox = FancyBboxPatch((-0.75, 0.0),
                                1.5, 100.0,
                                boxstyle=BoxStyle("Round", pad=0.005, rounding_size=0.75),
                                color=background_color,
                                mutation_aspect=3
                                )
        new_patches.append(p_bbox)
        
        patch = ax.patches[0]
        bb = patch.get_bbox()
        color=patch.get_facecolor()
        p_bbox = FancyBboxPatch((-0.75, bb.ymin),
                            1.5, abs(bb.height),
                            boxstyle=BoxStyle("Round", pad=0.005, rounding_size=0.75),
                            mutation_aspect=3,
                            color=fill_color
                            )
        patch.remove()
        new_patches.append(p_bbox)
        
        ax = plt.subplot(111)
        for patch in new_patches:
            ax.add_patch(patch)
        # add mouseover (color goes light green & gives label saying popularity)
        plt.xticks([])
        plt.yticks([0,25,50,75,100], fontproperties=font, color=fontcolor, horizontalalignment='center', verticalalignment='center')
        plt.ylim(0,100)
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        popularity_plot_uris.append(base64.b64encode(buffer.read()).decode('utf8'))
        buffer.close()
        
    return popularity_plot_uris

@app.route('/savePlaylist', methods=['POST'])
def save_playlist():
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect(url_for('login', _external=False))
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    data = request.get_json()
    name = data.get('name')
    songs = data.get('songs').split(',')
    user_id = sp.me()['id']
    sp.user_playlist_create(user=user_id, name=name, description="Playlist created by Spotify Playlist Sorter!")
    playlist_dict, _  = get_user_playlists_albums()
    for _, playlist in playlist_dict.items():
        if playlist['name'] == name:
            sp.user_playlist_add_tracks(user=user_id, playlist_id=playlist['id'], tracks=songs)
            return 'Playlist saved successfully'
    return 'Playlist not found'
   
@app.route('/deletePlaylist', methods=['POST'])
def delete_playlist():
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect(url_for('login', _external=False))
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    data = request.get_json()
    name = data.get('name')
    playlist_dict, _  = get_user_playlists_albums()
    for _, playlist in playlist_dict.items():
        if playlist['name'] == name:
            sp.current_user_unfollow_playlist(playlist_id=playlist['id'])
            return 'Playlist deleted successfully'
    return 'Playlist not found'   

# function to get the token info from the session
def get_token():
    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        # if the token info is not found, redirect the user to the login route
        redirect(url_for('login', _external=False))
    
    # check if the token is expired and refresh it if necessary
    now = int(time.time())
    is_expired = token_info['expires_at'] - now < 60
    if(is_expired):
        spotify_oauth = create_spotify_oauth()
        token_info = spotify_oauth.refresh_access_token(token_info['refresh_token'])

    return token_info

def create_spotify_oauth():
    with open('client-info.json', 'r') as f:
        client_info = json.load(f)
    return SpotifyOAuth(
        client_id = client_info['client_id'],
        client_secret = client_info['client_secret'],
        redirect_uri = url_for('redirect_page', _external=True),
        scope='user-library-read playlist-modify-public playlist-modify-private',
        cache_path="./cache.txt"
    )

# Function to clear the JSON data at program exit
def clear_json_data():
    with open('spotifyPlaylistOrganizer/data/songs.json', 'w') as file:
        json.dump({}, file)
        
# deletes cache file at program exit
def clear_cache():
    if os.path.exists("./cache.txt"):
        os.remove("./cache.txt")

atexit.register(clear_json_data)
atexit.register(clear_cache)

# about page
@app.route('/about')
def about_page():
    clear_json_data()
    return render_template('about.html')

if __name__=="__main__":
    app.run(debug=True)