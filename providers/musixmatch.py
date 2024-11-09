import json
import logging
import os

from time import time

from lrc import NoTokenException
from providers.getter import Getter
from song import Song

logger = logging.getLogger(__name__)

class Musixmatch(Getter):
    def __init__(self, token_dir: str):
        self.api_ep = 'https://apic-desktop.musixmatch.com/ws/1.1'
        self.api_token = None
        self.token_dir = token_dir
        self.api_tok_file = os.path.join(token_dir, 'mxm_api_token.json')

    def get_lyrics(self, song: Song, type: str = None):
        try: self.__get_api_token()
        except NoTokenException: raise

        tracks = self.__search(song.title, song.artist)
        compare = lambda t: f"{t['track']['track_name']} {t['track']['artist_name']} {t['track']['album_name']}"
        track = self._get_best_match(tracks, compare, song)
        if not track:
            return None

        track_id = track['track']['track_id']
        return self.__get_song_lyrics(track_id, type)

    def __get_api_token(self):
        token = self._find_token(self.api_tok_file)
        if token and self.api_token:
            self.api_token = token
            return

        headers = { 'Accept': 'application/json' }
        params = { 'app_id': 'web-desktop-app-v1.0' }
        url = f"{self.api_ep}/token.get"

        body = self._get(url, params=params, headers=headers)

        if not body:
            raise NoTokenException('Failed to get API token')
        
        token = {
            'token': body['message']['body']['user_token'],
            'expires_at': int(time()) + 600
        }

        with open(self.api_tok_file, 'w') as f:
            json.dump(token, f)
    
    def __get_song_lyrics(self, track_id, type):
        headers = { 'Accept': 'application/json' }
        params = {
            'app_id': 'web-desktop-app-v1.0',
            'usertoken': self.api_token,
            'track_id': track_id,
            'subtitle_format': 'plain' if type == 'plain' else 'lrc',
            'translation_fields_set': 'minimal'
        }
        url = f"{self.api_ep}/track.subtitle.get"

        body = self._get(url, params=params, headers=headers)
        
        if not body:
            return None

        return body['message']['body']['subtitle']['subtitle_body']
    
    def __search(self, track, artist):
        query = f'{track} {artist}'
        headers = { 'Accept': 'application/json' }
        params = {
            'app_id': 'web-desktop-app-v1.0',
            'usertoken': self.api_token,
            'q': query,
            'page': 1,
            'page_size': 5
        }
        url = f"{self.api_ep}/track.search"

        body = self._get(url, params=params, headers=headers)

        if not body:
            return None
        
        return body['message']['body']['track_list']