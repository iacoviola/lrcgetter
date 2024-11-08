import os
import json
import requests

from time import time

from lrc import NoMatchFoundException
from song import Song
from providers.getter import Getter

class Musixmatch(Getter):
    def __init__(self, token_dir: str):
        self.api_ep = 'https://apic-desktop.musixmatch.com/ws/1.1'
        self.api_token = None
        self.token_dir = token_dir
        self.api_tok_file = os.path.join(token_dir, 'mxm_api_token.json')

    def get_lyrics(self, song: Song, type: str = None):
        self.__get_api_token()

        tracks = self.__search(song.title, song.artist)
        if not tracks:
            return None
        compare = lambda t: f"{t['track']['track_name']} {t['track']['artist_name']} {t['track']['album_name']}"
        track = self._get_best_match(tracks, compare, song)
        if not track:
            return None

        track_id = track['track']['track_id']
        lyrics = self.__get_song_lyrics(track_id, type)
        return lyrics

    def __get_api_token(self):
        if self.__validate_token():
            return
        
        expiration = lambda t: t['expiration_time']
        token = self.__find_token(self.api_tok_file, expiration)
        if token:
            if not self.api_token:
                self.api_token = token
            return

        headers = { 'Accept': 'application/json' }
        params = { 'app_id': 'web-desktop-app-v1.0' }
        url = f"{self.api_ep}/token.get"

        body = self._get(url, params=params, headers=headers)

        if not body:
            raise Exception("Failed to get API token")
        
        token = {
            'user_token': body['message']['body']['user_token'],
            'expiration_time': int(time()) + 600
        }

        with open(self.api_tok_file, 'w') as f:
            json.dump(token, f)

    def __find_token(self, token_file, expiration_time):
        try:
            with open(token_file, 'r') as f:
                tok = json.load(f)
        except FileNotFoundError:
            return None

        if int(time()) > expiration_time(tok):
            return None

        return tok['user_token']

    def __validate_token(self):
        try:
            with open(self.api_tok_file, 'r') as f:
                tok = json.load(f)
        except FileNotFoundError:
            return False

        if int(time()) > tok['expiration_time']:
            return False

        if not self.api_token:
            self.api_token = tok['user_token']
        return True
    
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