# Spotify Playlist Organizer

## About
This is a simple Web App that allows a user to organize and generate new playlists from the songs in their saved albums and playlists based on similarities in each song.

## Getting Started
To start this application, first, navigate to the application directory and run the following line in the terminal to install all required libraries:
`pip install -r requirements.txt`

Then, go to `client-info.json` and replace the `client_id` and `client_secret` values with your client ID and client secret. 
![Picture of Client Credentials](/images/credentials.png)

For help finding these, follow the directions [here](https://stevesie.com/docs/pages/spotify-client-id-secret-developer-api). You will need to set up your Spotify Developer account if you have not already.

On the App Dashboard, go to settings and add the following redirect URI: `http://127.0.0.1:5000/redirect`

Congrats! You're now ready to run the application! To start it, run the following line in the terminal
`python spotifyPlaylistOrganizer/run.py`

The first time you run the application, you will be asked to agree to the terms and conditions. The app will not modify your Spotify without your express permission and will only create or delete new playlists. It will not affect your existing playlists or albums.
![Picture of Terms and Conditions](/images/terms_and_conditions.png).

Once you agree to the Terms and Conditions, you should be redirected to the Spotify login and the web page is up and running!

## Using the Webpage
Upon accessing the webpage, the user is immediately redirected to log in to their Spotify account.

![Picture of Login Page](/spotifyPlaylistOrganizer/static/images/spotify_login.png)

Once the user has successfully logged in to their account, they are redirected to the App's Home Page where they are prompted to select which of their saved playlists and albums they would like to organize into new playlists.
The user can also adjust their preferences for the way playlists are constructed and the number of playlists they wish to sort the songs into.

![Picture of Home Page](/spotifyPlaylistOrganizer/static/images/homepage.png)

The application then sorts the song into playlists based on the audio features of each song, such as danceability, energy, how acoustic it is, and more.
The newly-organized playlists are then displayed with a short couple of adjective descriptions of the qualities of songs in each playlist.

![Picture of Playlist Page](/spotifyPlaylistOrganizer/static/images/playlists.png)

The user can scroll through the playlists to view all of the songs in it and preview 30-second samples of each song by clicking the play button. By clicking on an artist or song name, users can navigate to their respective Spotify pages.

https://github.com/briesroncalli/spotify-playlist-organizer/assets/107960569/8fe9d64c-506b-463e-93d6-fcb986fafeed

Users can also explore the properties of each playlist from the 'Stats' tab to the left of each playlist, which displays the number of songs in the playlist as well as their average features, popularity, and duration.

https://github.com/briesroncalli/spotify-playlist-organizer/assets/107960569/eb0d5966-c560-43a3-8e92-ff7b87e7451f

If a user likes a playlist, they can save it by clicking the 'Save Playlist' button in the top right of the playlist. The button updates to show that it has been saved.
If a user saves a playlist by accident, they can remove it from their playlist by simply reclicking the updated button.

https://github.com/briesroncalli/spotify-playlist-organizer/assets/107960569/f9d8f0ea-112c-4c21-a9c2-1780e81f190b

## Implementation
The application uses the [Spotify API](https://developer.spotify.com/documentation/web-api) to access song information in a user's saved playlists and albums. It feeds features Spotify collects about the audio features of each song to a hierarchical clustering model. The user can make selections about their preferences for the resulting clusters on the App's Home Page. These preferences are then translated into parameters and instructions for the clustering algorithm, which returns playlist grouping songs together based on similarity.

More information about the data the algorithm uses to cluster songs can be found at [Spotify API Audio Features](https://developer.spotify.com/documentation/web-api/reference/get-audio-features).

The hierarchical clustering algorithm is implemented in `Python` with the use of the `scipy` library.

See the full project on [GitHub](https://github.com/briesroncalli/spotify-playlist-organizer).
