import json
import logging
import os

from time import time

from lrc import NoTokenException
from providers.getter import Getter
from song import Song

logger = logging.getLogger(__name__)

class Spotify(Getter):

    API_EP = 'https://api.spotify.com/v1'
    API_TOK_EP = 'https://accounts.spotify.com/api/token'
    LRC_TOK_EP = 'https://open.spotify.com/get_access_token?reason=transport&productType=web_player'
    LRC_EP_HEAD = 'https://spclient.wg.spotify.com/color-lyrics/v2/track'
    LRC_EP_TAIL = '?format=json&vocalRemoval=false&market=from_token'

    USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.0.0 Safari/537.36'

    def __init__(self, client_id, client_secret, sp_dc, tokens_dir):
        self.CLIENT_ID = client_id
        self.CLIENT_SECRET = client_secret
        self.SP_DC = sp_dc
        
        self.api_token = None
        self.lrc_token = None
        self.tokens_dir = tokens_dir

        if not os.path.exists(tokens_dir):
            os.makedirs(tokens_dir)

        self.api_tok_file = os.path.join(tokens_dir, 'api_token.json')
        self.lrc_tok_file = os.path.join(tokens_dir, 'lrc_token.json')

    def get_lyrics(self, song: Song, type: str = None):
        try: self.__get_api_token()
        except NoTokenException: raise
        
        tracks = self.__search(song.title, song.artist)        
        compare = lambda t: f"{t['name']} {' '.join([a['name'] for a in t['artists']])} {t['album']['name']}"
        track = self._get_best_match(tracks, compare, song)

        if not track:
            return None

        track_url = track['external_urls']['spotify']
        track_id = track_url.split('/')[-1]

        try: self.__get_lrc_token()
        except NoTokenException: raise

        lyrics = self.__get_song_lyrics(track_id)

        return self.__parse_lyrics(lyrics, type)

    def __ms_to_time(self, ms):
        mins = ms // 1000 // 60
        secs = ms // 1000 % 60
        ms = ms % 1000 // 10
        return f"{mins:02d}:{secs:02d}.{ms:02d}"

    def __parse_lyrics(self, lyrics, type):
        if not lyrics:
            return None
        if type == 'synced':
            return self.__get_synced(lyrics)
        return self.__get_plain(lyrics)
    
    def __get_synced(self, lyrics):
        lrc_str = ''
        lines = lyrics['lyrics']['lines']

        for line in lines:
            lrc_str += f"[{self.__ms_to_time(int(line['startTimeMs']))}] {line['words']}\n"

        return lrc_str
    
    def __get_plain(self, lyrics):
        lines = lyrics['lyrics']['lines']

        return "\n".join([line['words'] for line in lines])

    def __get_song_lyrics(self, track_id):
        headers = {
            'Authorization': f'Bearer {self.lrc_token}',
            'User-Agent': self.USER_AGENT,
            'App-platform': 'WebPlayer',
            'Accept': 'application/json'
        }
        url = f"{self.LRC_EP_HEAD}/{track_id}{self.LRC_EP_TAIL}"

        body = self._get(url, headers=headers)

        if not body:
            return None
        return body

    def __get_api_token(self):
        token = self._find_token(self.api_tok_file)
        if token and not self.api_token:
            self.api_token = token
            return
        
        headers = { 'Content-Type': 'application/x-www-form-urlencoded' }
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET
        }
        url = self.API_TOK_EP

        body = self._post(url, data, headers)

        if not body:
            raise NoTokenException("Failed to get API token")
        
        self.api_token = body['access_token']

        body['token'] = body.pop('access_token') 
        body['expires_at'] = int(time()) + body.pop('expires_in')

        with open(self.api_tok_file, 'w') as f:
            json.dump(body, f)
    
    def __get_lrc_token(self):
        token = self._find_token(self.lrc_tok_file)
        if token and not self.lrc_token:
            self.lrc_token = token
            return
        
        headers = {
            'User-Agent': self.USER_AGENT,
            'App-platform': 'WebPlayer',
            'content-type': 'text/html; charset=utf-8',
            'cookie': f"sp_dc={self.SP_DC}"
        }
        body = self._get(self.LRC_TOK_EP, headers=headers)

        if not body or body['isAnonymous']:
            raise NoTokenException("Failed to get LRC token")
        
        self.lrc_token = body['accessToken']

        body['token'] = body.pop('accessToken')
        body['expires_at'] = body.pop('accessTokenExpirationTimestampMs') // 1000
        with open(self.lrc_tok_file, 'w') as f:
            json.dump(body, f)

    def __search(self, track, artist):
        query = f'{track} artist:{artist}'
        headers = { 'Authorization': f'Bearer {self.api_token}' }
        params = {
            'q': query,
            'type': 'track'
        }
        url = f"{self.API_EP}/search"

        body = self._get(url, params=params, headers=headers)

        if not body:
            return None
        return body['tracks']['items']