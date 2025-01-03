import os, spotipy, webbrowser
from dotenv import load_dotenv
# custom files
import api

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
    file.close()

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

    SCOPES: list[str] = [
        "playlist-modify-public", "playlist-modify-private", # needed to add songs to a playlist
        "playlist-read-private", "playlist-read-collaborative", # needed to read the playlists of the user
    ]

    print("enter the link or uri to your spotify account (go to your profile, right click on your name, and select copy spotify uri or copy link to profile) - this is needed for your spotify account id:")
    user_id: str = api.parse_user_id(input())
    spotify: spotipy.Spotify = api.create_spotify_api_handler(user_id, os.getenv("SPOTIFY_CLIENT_ID"), os.getenv("SPOTIFY_CLIENT_SECRET"), os.getenv("SPOTIFY_REDIRECT_URI"), SCOPES)

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

    user_playlists_raw: list[dict] = spotify.current_user_playlists(limit=50)["items"] # type: ignore # same reason as last time
    user_playlists: dict[str, str] = {}
    for item in user_playlists_raw:
        user_playlists[item["name"]] = item["uri"]

    for playlist, song in songs.items(): # type: ignore # i have no idea why its wrong or how to fix it and it works so
        if playlist not in user_playlists:
            if playlist[0] == "+":
                api.create_playlist(playlist, user_id, spotify)
            else:
                while playlist not in user_playlists:
                    match input(f"playlist {playlist} does not exist and is not marked to be created. do you want to create it, skip it, or change that playlist to another playlist? (1, 2, 3)"):
                        case 1:
                            api.create_playlist(playlist, user_id, spotify)
                            user_playlists.append(playlist)
                            break
                        case 2:
                            continue
                        case 3:
                            playlist = input("enter the name of the changed playlist: ")
        elif playlist in user_playlists:
            track_uris: list[str] = []
            for track in song:
                search_result: str | None = api.search_uri("track", track, spotify)
                if search_result == None:
                    print(f"{track} either does not exist or the inputted search was too far from the original name. skipping track.")
                    continue
                track_uris.append(search_result) # type: ignore # i handle this already
            playlist_uri = user_playlists[playlist]
            api.add_item_to_playlist(track_uris, playlist_uri, user_id, spotify)
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
