import os, sys
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
    if len(sys.argv) > 1:
        file_path: str = sys.argv[1]
    else:
        file_path: str = input("enter the path of the file you want to organize: ")
    if not check_file_validity(file_path):
        return 1

    file = open(file_path, 'r')
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
    spotify = api.Spotify(
        user_id=user_id,
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scopes=SCOPES
    )

    # separate the file into sections
    song_lines: list[str] = []
    artist_lines: list[str] = []
    current_section: str = ""

    for line in lines:
        if "Songs" in line:
            current_section = "Songs"
        elif "Artists" in line:
            current_section = "Artists"
        else:
            if current_section == "Songs":
                song_lines.append(line)
            elif current_section == "Artists":
                artist_lines.append(line)

    # get the playlists of each song
    song_assignments: dict[str, list[str]] = {
        "songs": []
    }
    for song_line in song_lines:
        split_line: list[str] = [piece.strip() for piece in song_line.split("/")]
        song_name: str = split_line[0].strip()
        playlist_line: list[str] = [playlist_name.strip() for playlist_name in split_line[1].split()]
        for playlist in playlist_line:
            if playlist != "!songs":
                if playlist not in song_assignments:
                    song_assignments[playlist] = []
                song_assignments[playlist].append(song_name)
        del playlist
        if "!songs" not in playlist_line:
            song_assignments["songs"].append(song_name)

    for playlist, songs in song_assignments.items():
        if playlist not in spotify.playlists:
            if playlist[0] == "+":
                spotify.create_playlist(playlist)
            else:
                while playlist not in spotify.playlists:
                    match input(f"playlist {playlist} does not exist and is not marked to be created. do you want to create it, skip it, or change that playlist to another playlist? (1, 2, 3)"):
                        case 1:
                            playlist_data: dict[str, str] = spotify.create_playlist(playlist)
                            spotify.playlists.update(playlist_data)
                            break
                        case 2:
                            continue
                        case 3:
                            playlist = input("enter the name of the changed playlist: ")
        elif playlist in spotify.playlists:
            track_uris: list[str] = []
            for track in songs:
                search_result: str | None = spotify.search(track, "track")
                if search_result == None:
                    print(f"{track} either does not exist or the inputted search was too far from the original name. skipping track.")
                    continue
                track_uris.append(search_result)
            spotify.add_track_to_playlist(track_uris, spotify.playlists[playlist], playlist)
        else:
            print("unknown error")
            return 1
    print("successful")

    return 0

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nexiting program...")
