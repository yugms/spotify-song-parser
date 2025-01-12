import urllib.parse as parse, base64, requests, secrets, webbrowser, platformdirs, json, time, os, cryptocode, sys

class Spotify:
    """
    Object to handle the Spotify API. Supply a user id, client id, client secret, redirect uri, scope(s), and whether you want to auto authenticate (authenticate and authorize spotify after initiating class or do it with the "spotify" function)
    """
    def __init__(self, user_id: str, client_id: str, client_secret: str, redirect_uri: str, scopes: list[str], auto_authenticate: bool = True) -> None:
        self.user_id: str = user_id
        self.client_id: str  = client_id
        self.client_secret: str = client_secret
        self.redirect_uri: str = redirect_uri
        self.scope: str = ' '.join(scopes)
        self.absent_credentials: bool = False
        self.basic_auth: str = f"Basic {base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()}"
        self.authentication_url: str = "https://accounts.spotify.com/authorize"
        self.authorization_url: str = "https://accounts.spotify.com/api/token"
        self.api_url: str = "https://api.spotify.com/v1"

        # * check to make sure client id, client secret, and redirect uri exist
        if not self.client_id or not self.client_id.strip():
            print("no client id present. if you loaded the variables from an .env file, this means that the variable either does not exist/was misspelled or is empty")
            self.absent_credentials = True
        if not self.client_secret or not self.client_secret.strip():
            print("no client secret present. if you loaded the variables from an .env file, this means that the variable either does not exist/was misspelled or is empty")
            self.absent_credentials = True
        if not self.redirect_uri or not self.redirect_uri.strip():
            print("no redirect uri present. if you loaded the variables from an .env file, this means that the variable either does not exist/was misspelled or is empty")
            self.absent_credentials = True

        if self.absent_credentials: sys.exit("exiting program: absent credentials")

        self.CACHE_PATH: str = platformdirs.user_cache_dir("spotify-song-parser", "yugms")
        self.CACHE_FILE_PATH: str = os.path.join(self.CACHE_PATH, f"{self.user_id}.json")
        os.makedirs(self.CACHE_PATH, exist_ok=True)

        self.DATA_TO_ENCRYPT = ["access_token", "refresh_token"]

        if not auto_authenticate: return
        # authenticate spotify
        authentication_results = self.spotify()
        if "fail" in authentication_results: sys.exit("exiting program: authentication/authorization fail")
        self.access_token: str = authentication_results
        self.playlists: dict[str, str] = self.__get_playlists()

    def get_cached_data(self) -> str:
        if not os.path.exists(self.CACHE_FILE_PATH): return "fail: cache file for user does not exist"
        print("attempting to retrieve cached token")
        with open(self.CACHE_FILE_PATH, "r") as file:
            content = json.load(file)
        for item in self.DATA_TO_ENCRYPT:
            content[item] = cryptocode.decrypt(content[item], self.user_id)
        if time.time() < float(content["timestamp"]) + float(content["expires_in"]):
            print("cached token is valid. using cached token")
            return content["access_token"] # type: ignore # idk im tired
        return "fail: cached token invalid"

    def cache_data(self, data: dict) -> None:
        for item in self.DATA_TO_ENCRYPT: data[item] = cryptocode.encrypt(data[item], self.user_id)
        with open(self.CACHE_FILE_PATH, "w") as file:
            file.write(json.dumps(data))

    def authenticate_spotify(self) -> str:
        state: str = secrets.token_urlsafe(16) # state to ensure proper authentication
        auth_url: str = self.authentication_url + "?" + parse.urlencode({
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": self.scope
        })
        print("opening browser to authenticate spotify. please authenticate this app. once authenticated, copy the link you were redirected to and enter it below.")
        try:
            webbrowser.open(auth_url)
        except:
            print(f"error while opening browser. please manually navigate to the link below:\n{auth_url}")
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
        else: print("authentication failed for unknown reason"); return "authentication fail: unknown reason"
        return authorization_code

    def authorize_spotify(self, authorization_code: str) -> list[str | dict]:
        if not authorization_code: return ["authorization fail: no authorization code present"]
        access_token_results: requests.Response = \
        requests.post(
            self.authorization_url,
            data={
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": self.redirect_uri
            }, headers={
                "Authorization": self.basic_auth,
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        if access_token_results.status_code == 200:
            access_token: str = access_token_results.json()["access_token"]
        else: return [f"authorization fail: {access_token_results.json()["error"]}" if "error" in access_token_results.json() else f"authorization fail: error code {access_token_results.status_code}"]

        print("authorization successful. caching token...")

        new_cache_contents: dict = access_token_results.json()
        new_cache_contents.update({
            "timestamp": time.time()
        })

        return [access_token, new_cache_contents]

    def spotify(self, check_cache:bool=True) -> str:
        # * check if cached token exists, and if it does, retrieve it
        if check_cache:
            cache_results: str = self.get_cached_data()
            if "fail" not in cache_results:
                return cache_results
            else: print(f"{cache_results.split(": ")[1]}. re-authenticating")
        # * authenticates spotify
        authentication_result: str = self.authenticate_spotify()
        if "fail" in authentication_result: sys.exit(authentication_result)
        authorization_result: list = self.authorize_spotify(authentication_result)
        access_token: str = authorization_result[0]
        if "authorization fail" in access_token: sys.exit(access_token)
        if len(authorization_result) > 1:
            self.cache_data(authorization_result[1])
        return access_token

    def search(self, query: str, type: str) -> str | None:
        url: str = self.api_url + "/search"
        response: requests.Response = requests.get(
            url=url,
            params={
                "q": query,
                "type": type,
                "market": "ES"
            }, headers={
                "Authorization": f"Bearer {self.access_token}"
            }
        )
        if response.status_code == 401:
            print("access token expired. re-authenticating...")
            self.access_token = self.spotify(check_cache=False)
            response = requests.get(
                url=url,
                params={
                    "q": query,
                    "type": type,
                    "market": "ES",
                    "offset": 0
                }, headers={
                    "Authorization": f"Bearer {self.access_token}"
                }
            )
        if response.status_code != 200: sys.exit("unknown error happened.")

        data: dict = response.json()
        uri: str | None
        try:
            uri = data[f"{type}s"]["items"][0]["uri"]
        except:
            uri = None
        return uri

    def __get_playlists(self) -> dict[str, str]:
        url = self.api_url + "/me/playlists"
        response: requests.Response = requests.get(url=url, params={"limit": 50,}, headers={"Authorization": f"Bearer {self.access_token}"})
        if response.status_code == 401:
            print("access token expired. re-authenticating...")
            self.access_token = self.spotify(check_cache=False)
            response = requests.get(url=url, params={"limit": 50,}, headers={"Authorization": f"Bearer {self.access_token}"})
        if response.status_code != 200: sys.exit("unknown error happened.")

        data: dict = response.json()
        return {item["name"]: item["uri"] for item in data["items"]}

    def add_track_to_playlist(self, track_uris: list[str], playlist_uri: str) -> None:
        playlist_id: str = playlist_uri.split(":")[-1]
        tracks = [track.strip() for track in track_uris]
        url: str = self.api_url + f"/playlists/{playlist_id}/tracks"
        response: requests.Response = requests.post(
            url=url,
            json={
                "position": 0,
                "uris": tracks
            }, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}"
            }
        )
        if response.status_code == 401:
            print("access token expired. re-authenticating...")
            self.access_token = self.spotify(check_cache=False)
            response = requests.post(
                url=url,
                json={
                    "position": 0,
                    "uris": tracks
                }, headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.access_token}"
                }
            )
        if response.status_code != 201: sys.exit("unknown error occurred")

    def create_playlist(self, playlist_name: str) -> dict[str, str]:
        url: str = self.api_url + f"/users/{self.user_id}/playlists"
        response: requests.Response = requests.post(
            url=url,
            json={
                "name": playlist_name,
                "description": f"playlist named {playlist_name}"
            }, headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        )

        if response.status_code == 401:
            print("access token expired. re-authenticating...")
            self.access_token = self.spotify(check_cache=False)
            response = requests.post(
                url=url,
                json={
                    "name": playlist_name,
                    "description": f"playlist named {playlist_name}"
                }, headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
            )
        if response.status_code != 201: sys.exit("unknown error occurred")

        data: dict = response.json()
        return {data["name"]: data["uri"]}


def parse_user_id(raw_input: str) -> str:
    '''parse a spotify user link or uri to get the user id'''
    if "https://open.spotify.com/user/" in raw_input:
        user_id = raw_input.split("/")[-1]
        user_id = user_id.split("?")[0] if "?" in user_id else user_id
    elif "spotify:user:" in raw_input:
        user_id = raw_input.split(":")[-1]
    else: user_id = raw_input
    return user_id