import os, spotipy, webbrowser
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

def search_track(track: str, sp: spotipy.Spotify) -> str:
    '''search for a track on spotify'''
    results: dict[str, dict] = sp.search(q=track, limit=1, type="track", market="ES") # type: ignore # i dont feel like writing out the entire type structure of the api call response theres no point
    uri: str = results["tracks"]["items"][0]["uri"]
    return uri

def add_item_to_playlist(track_uris: list[str], playlist_uri: str, user_id:str, sp: spotipy.Spotify) -> None:
    '''add track(s) to a playlist'''
    sp.playlist_add_items(playlist_id=playlist_uri, items=track_uris)

def create_playlist(user_id: str, playlist_name: str, sp: spotipy.Spotify) -> None:
    '''create a playlist for the user'''
    sp.user_playlist_create(user=user_id, name=playlist_name, public=True, collaborative=False)

def check_file_validity(file_name: str) -> bool:
    '''check if a file exists and is a text file'''
    try:
        file = open(file_name, 'r')
        file.close()
        return True
    except FileNotFoundError:
        print(f"file {file_name} not found")
        return False
    except UnicodeDecodeError:
        print(f"file {file_name} is not a text file")
        return False
    except Exception as e:
        print(f"an error occurred: {e}")
        return False

def check_file_format(content: str) -> bool:
    '''check if a file is in the correct format'''
    return "Songs" in content and "Artists" in content

def main() -> int:
    '''main function'''
    # open and read the file
    file_name: str = input("enter the path of the file you want to organize: ")
    if not check_file_validity(file_name):
        return 1

    file = open(file_name, 'r')
    content = file.read()
    lines: list[str] = [line.strip() for line in content.split("\n") if not(line.isspace() or not line)] # remove empty lines

    # check if the file is in the correct format
    if not check_file_format(content):
        print("file format is not valid")
        return 1

    # read client id and secret from environment variables
    load_dotenv()
    if "SPOTIFY_CLIENT_ID" not in os.environ:
        print("spotify client id is not present. please create a .env file with the client id variable named \"SPOTIFY_CLIENT_ID\"")
        return 1
    if "SPOTIFY_CLIENT_SECRET" not in os.environ:
        print("spotify client secret is not present. please create a .env file with the client secret variable named \"SPOTIFY_CLIENT_SECRET\"")
        return 1
    if "SPOTIFY_REDIRECT_URI" not in os.environ:
        print("spotify redirect uri is not present. please create a .env file with the redirect uri variable named \"SPOTIFY_REDIRECT_URI\"")
        return 1
    SPOTIFY_CLIENT_ID: str | None = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET: str | None = os.getenv("SPOTIFY_CLIENT_SECRET")
    SPOTIFY_REDIRECT_URI: str | None = os.getenv("SPOTIFY_REDIRECT_URI")

    SCOPES: list[str] = [
        "playlist-modify-public", "playlist-modify-private", # needed to add songs to a playlist
        "playlist-read-private", "playlist-read-collaborative", # needed to read the playlists of the user
    ]

    # authenticate with spotify

    print("enter the link or uri to your spotify account (go to your profile, right click on your name, and select copy spotify uri or copy link to profile) - this is needed for your spotify account id:")
    user_id_unprocessed: str = input("")
    user_id: str = ""

    if "https://open.spotify.com/user/" in user_id_unprocessed:
        user_id = user_id_unprocessed.split("/")[-1]
        user_id = user_id.split("?")[0] if "?" in user_id else user_id
    elif "spotify:user:" in user_id_unprocessed:
        user_id = user_id_unprocessed.split(":")[-1]
    else: user_id = user_id_unprocessed

    auth_manager: SpotifyOAuth = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SCOPES,
        cache_path=".cache-" + user_id
    )
    sp: spotipy.Spotify = spotipy.Spotify(auth_manager=auth_manager)
    # separate the file into sections
    songs_list: list[str] = []
    artists: list[str] = []
    current_section: str = ""

    for line in lines:
        if "Songs" in line:
            current_section = "Songs"
        elif "Artists" in line:
            current_section = "Artists"
        else:
            if current_section == "Songs":
                songs_list.append(line)
            elif current_section == "Artists":
                artists.append(line)

    # get the playlists of each song
    songs: dict[str, list[str]] = {
        "songs": []
    }
    for s in songs_list:
        processed_line: list[str] = s.split(" / ")
        song: str = processed_line[0].strip()
        playlist_line: list[str] = [p.strip() for p in processed_line[1].split()]
        for playlist in playlist_line:
            if playlist != "!songs":
                if playlist not in songs:
                    songs[playlist] = []
                songs[playlist].append(song)
        if "!songs" not in playlist_line:
            songs["songs"].append(song)

    user_playlists_raw: list[dict] = sp.current_user_playlists(limit=50)["items"] # type: ignore # same reason as last time
    user_playlists: dict[str, str] = {}
    for item in user_playlists_raw:
        user_playlists[item["name"]] = item["uri"]

    for playlist, song in songs.items(): # type: ignore # i have no idea why its wrong or how to fix it and it works so
        if playlist not in user_playlists:
            if playlist[0] == "+":
                create_playlist(user_id, playlist, sp)
            else:
                while playlist not in user_playlists:
                    match input(f"playlist {playlist} does not exist and is not marked to be created. do you want to create it, skip it, or change that playlist to another playlist? (1, 2, 3)"):
                        case 1:
                            create_playlist(user_id, playlist, sp)
                            user_playlists.append(playlist)
                            break
                        case 2:
                            continue
                        case 3:
                            playlist = input("enter the name of the changed playlist: ")
        elif playlist in user_playlists:
            track_uris: list[str] = [search_track(track, sp) for track in song]
            playlist_uri = user_playlists[playlist]
            add_item_to_playlist(track_uris, playlist_uri, user_id, sp)
        else:
            print("unknown error")
            return 1
    print("successful")

    return 0

if __name__ == '__main__':
    try:
        response = main()
        if response != 0:
            print("an error occurred")
    except KeyboardInterrupt:
        print("\nexiting program...")
    except spotipy.SpotifyException as s:
        print(f"error with spotify: {s}")
    except Exception as e:
        print(f"error: {e}")

# TODO: find the top songs of each artist
# TODO: add the top songs of each artist to the corresponding playlist