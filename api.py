import urllib.parse as parse, base64, requests, secrets, webbrowser, platformdirs, json, time, typing, os, dotenv, cryptocode

def parse_user_id(raw_input: str) -> str:
    '''parse a spotify user link or uri to get the user id'''
    if "https://open.spotify.com/user/" in raw_input:
        user_id = raw_input.split("/")[-1]
        user_id = user_id.split("?")[0] if "?" in user_id else user_id
    elif "spotify:user:" in raw_input:
        user_id = raw_input.split(":")[-1]
    else: user_id = raw_input
    return user_id

def refresh_token(refresh_token: str, client_id: str, client_secret: str) -> str | dict[str, int | str]:
    url = "https://accounts.spotify.com/api/token"
    response = requests.post(url, {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic: {client_id}:{client_secret}"
    })
    if response.status_code != 200:
        return f"refresh fail: error code {response.status_code}"
    return response.json() # type: ignore # this almost always returns a dict so...

def cache_data(data: dict[typing.Any, typing.Any], path: str, user_id: str, data_to_encrypt: list[str]) -> None:
    for item in data_to_encrypt:
        data[item] = cryptocode.encrypt(data[item], user_id)
    with open(path, "w") as file:
        file.write(json.dumps(data))

def retrieve_cached_data(path: str, user_id: str, encrypted_items: list[str]) -> dict[typing.Any, typing.Any]:
    with open(path, "r") as file:
        content = json.load(file)
        for item in encrypted_items:
            content[item] = cryptocode.decrypt(content[item], user_id)
        return content # type: ignore #  i just want to finish this project

def authorize_spotify(client_id: str | None, client_secret: str | None, redirect_uri: str | None, user_id: str, scopes: list[str]) -> str:
    '''
    authorizes spotify web api using authorization code flow
    returns access token or reason for authorization fail
    '''
    # * check to make sure client id, secret and redirect uri actually exist
    if not client_id or not client_id.strip():
        print("no client id present. if you loaded the variables from an .env file, this means that the variable either does not exist/was misspelled or is empty")
        return "authentication fail: no client id"
    if not client_secret or not client_secret.strip():
        print("no client secret present. if you loaded the variables from an .env file, this means that the variable either does not exist/was misspelled or is empty")
        return "authentication fail: no client secret"
    if not redirect_uri or not redirect_uri.strip():
        print("no redirect uri present. if you loaded the variables from an .env file, this means that the variable either does not exist/was misspelled or is empty")
        return "authentication fail: no redirect uri"

    # * creates a cache folder to store access tokens
    CACHE_PATH: str = platformdirs.user_cache_dir("spotify-song-parser", "yugms")
    CACHE_FILE: str = os.path.join(CACHE_PATH, f"{user_id}.json")
    os.makedirs(CACHE_PATH, exist_ok=True)
    print("cache folder generated")

    DATA_TO_ENCRYPT = ["access_token", "refresh_token"]

    # * check to see if cache token already exists
    if os.path.exists(CACHE_FILE):
        print("cache file exists. attempting to retrieve cached token")
        cached_data = retrieve_cached_data(CACHE_FILE, user_id, DATA_TO_ENCRYPT)
        if time.time() < float(cached_data["timestamp"]) + float(cached_data["expires_in"]):
            print("cached token is valid. using cached token")
            return cached_data["access_token"] # type: ignore # idk im tired
        else:
            print("cached token invalid. attempting to refresh token")
            refresh_token_response: str | dict[str, int | str] = refresh_token(cached_data["refresh_token"], client_id, client_secret)
            if type(refresh_token_response) == str: print(f"{refresh_token_response}. manually authenticating...")
            else:
                print("successfully refreshed token")
                refresh_token_response.update({ # type: ignore # i handle this
                    "timestamp": int(time.time())
                })
                cache_data(refresh_token_response, CACHE_FILE, user_id, DATA_TO_ENCRYPT) # type: ignore # I HANDLE THIS god i am going to stop using mypy
                return refresh_token_response["access_token"] # type: ignore # AHHHHHHHHH



    BASE_URL: str = "https://accounts.spotify.com"
    AUTHENTICATION_URL: str = f"{BASE_URL}/authorize"
    ACCESS_TOKEN_URL: str = f"{BASE_URL}/api/token"

    # * makes user authenticate app
    state: str = secrets.token_urlsafe(16) # state to ensure proper authentication
    scope_string: str = " ".join(scopes)
    auth_url: str = AUTHENTICATION_URL + "?" + parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": scope_string
    })
    print("opening browser to authenticate spotify. please authenticate this app. once authenticated, copy the link you were redirected to and enter it below.")
    webbrowser.open(auth_url)
    authorized_url: str = input("please input the link you were redirected to: ")
    authorization_result: dict[str, list[str]] = parse.parse_qs(parse.urlparse(authorized_url).query)
    if "error" in authorization_result:
        print(f"error in authenticating: {authorization_result["error"][0]}")
        return f"authentication fail: {authorization_result['error'][0]}"
    if not secrets.compare_digest(authorization_result["state"][0], state):
        print("states of requests do not match. quitting program to prevent infiltration into account.")
        return "authentication fail: states do not match"
    if "code" in authorization_result:
        authorization_code: str = authorization_result["code"][0]
    else: return "authentication fail: unknown reason"

    # * gets access token
    access_token_results: requests.Response = \
    requests.post(
        ACCESS_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": redirect_uri
        }, headers={
            "Authorization": f"Basic {base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    if access_token_results.status_code == 200:
        access_token: str = access_token_results.json()["access_token"]
    else: return f"authorization fail: {access_token_results.json()["error"]}" if "error" in access_token_results.json() else f"authorization fail: error code {access_token_results.status_code}"

    print("authorization successful. caching token...")

    new_cache_contents: dict[str, str | float] = access_token_results.json()
    new_cache_contents.update({
        "timestamp": time.time()
    })

    cache_data(new_cache_contents, CACHE_FILE, user_id, DATA_TO_ENCRYPT)

    return access_token

dotenv.load_dotenv()
print(authorize_spotify(
    os.getenv("SPOTIFY_CLIENT_ID"),
    os.getenv("SPOTIFY_CLIENT_SECRET"),
    os.getenv("SPOTIFY_REDIRECT_URI"),
    "31wuo5slsvqcv6hnox2zjxyrahqe",
    [
        "playlist-modify-public", "playlist-modify-private", # needed to add songs to a playlist
        "playlist-read-private", "playlist-read-collaborative", # needed to read the playlists of the user
    ]
))