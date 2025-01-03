from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

def parse_user_id(raw_input: str) -> str:
    '''parse a spotify user link or uri to get the user id'''
    if "https://open.spotify.com/user/" in raw_input:
        user_id = raw_input.split("/")[-1]
        user_id = user_id.split("?")[0] if "?" in user_id else user_id
    elif "spotify:user:" in raw_input:
        user_id = raw_input.split(":")[-1]
    else: user_id = raw_input
    return user_id

def create_playlist(name: str, user_id: str, spotify: Spotify) -> None:
    '''create a playlist for a user'''
    spotify.user_playlist_create(user_id, name, True, False, "")

def add_item_to_playlist(tracks: list[str], playlist: str, user_id: str, sp: Spotify) -> None:
    '''add track(s) to a playlist'''
    sp.playlist_add_items(playlist_id=playlist, items=tracks)

def search_uri(type: str, query: str, spotify: Spotify) -> str | None:
    '''search spotify for whatever the user wants and returns uri'''
    result = spotify.search(query, 1, 0, type, "ES")
    return result[type]["items"][0]["uri"] if result != None else None

def create_spotify_api_handler(user_id:str, client_id: str|None, client_secret: str|None, redirect_uri: str, scopes: list[str]) -> Spotify:
    '''creates and returns a spotify object using spotify authorization code'''
    auth_manager: SpotifyOAuth = SpotifyOAuth(client_id, client_secret, redirect_uri, None, scopes, ".cache-" + user_id)
    return Spotify(auth_manager=auth_manager)