import requests
import json
import logging
import os

from time import time

from providers.getter import Getter
from song import Song
from lrc import NoMatchFoundException

logger = logging.getLogger(__name__)

class Spotify(Getter):
    def __init__(self, client_id, client_secret, sp_dc, tokens_dir):
        self.client_id = client_id
        self.client_secret = client_secret
        self.sp_dc = sp_dc
        self.api_token = None
        self.lrc_token = None
        self.tokens_dir = tokens_dir

        if not os.path.exists(tokens_dir):
            os.makedirs(tokens_dir)

        self.api_tok_file = os.path.join(tokens_dir, 'api_token.json')
        self.lrc_tok_file = os.path.join(tokens_dir, 'lrc_token.json')

        self.api_ep = 'https://api.spotify.com/v1'
        self.api_tok_ep = 'https://accounts.spotify.com/api/token'
        self.lrc_tok_ep = 'https://open.spotify.com/get_access_token?reason=transport&productType=web_player'
        self.lrc_ep = 'https://spclient.wg.spotify.com/color-lyrics/v2/track/'
        self.lrc_ep_end = '?format=json&vocalRemoval=false&market=from_token'

        self.user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.0.0 Safari/537.36'

    def get_lyrics(self, song: Song, type: str = None):

        self.__obtain_api_token()

        tracks = self.__search(song.title, song.artist)

        track, aff, probs = self._get_chosen_track(tracks, song)

        track_url = track['external_urls']['spotify']

        self.__obtain_lrc_token()
        lyrics = self.__get_song_lyrics(track_url)

        return self.__parse_lyrics(lyrics, type), aff, probs

    def _get_song(self, obj: dict):
        title = obj['name']
        artist = ";".join([artist['name'] for artist in obj['artists']])
        album = obj['album']['name']
        duration = float(obj['duration_ms']) / 1000

        return Song(title, artist, album, duration)

    def __ms_to_time(self, ms):
        mins = ms // 1000 // 60
        secs = ms // 1000 % 60
        ms = ms % 1000 // 10
        return f"{mins:02d}:{secs:02d}.{ms:02d}"

    def __parse_lyrics(self, lyrics, type):
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

    def __get_song_lyrics(self, track_url):
        track_id = track_url.split('/')[-1]
        headers = {
            'Authorization': f'Bearer {self.lrc_token}',
            'User-Agent': self.user_agent,
            'App-platform': 'WebPlayer',
            'Accept': 'application/json'
        }

        response = requests.get(f"{self.lrc_ep}{track_id}{self.lrc_ep_end}", headers=headers)

        logger.debug(response.url)
        if response.status_code == 404:
            raise NoMatchFoundException("The song is on Spotify but the lyrics are not available, fallback to another provider")
        if response.status_code != 200:
            raise Exception(f"Failed to get lyrics, error code:{response.status_code}" + response.text)
        
        return response.json()

    def __obtain_api_token(self):
        if self.__validate('api'):
            return
        
        token_infos = self.__get_api_token()
        self.api_token = token_infos['access_token']

        token_infos['generated_at'] = int(time())

        with open(self.api_tok_file, 'w') as f:
            json.dump(token_infos, f)

    def __obtain_lrc_token(self):
        if self.__validate('lrc'):
            return
        
        token_infos = self.__get_lrc_token()
        self.lrc_token = token_infos['accessToken']

        with open(self.lrc_tok_file, 'w') as f:
            json.dump(token_infos, f)

    def __get_api_token(self):
        # Get token from Spotify API
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        response = requests.post(self.api_tok_ep, headers=headers, data=data)

        if response.status_code != 200:
            raise Exception(f'Failed to get token, error code:{response.status_code}' + response.text)
        
        return response.json()
    
    def __get_lrc_token(self):
        headers = {
            'User-Agent': self.user_agent,
            'App-platform': 'WebPlayer',
            'content-type': 'text/html; charset=utf-8',
            'cookie': f"sp_dc={self.sp_dc}"
        }

        response = requests.get(self.lrc_tok_ep, headers=headers)

        body = response.json()

        if response.status_code != 200 or body['isAnonymous']:
            raise Exception(f'Failed to get token, error code:{response.status_code}' + response.text)
        
        return body
    
    def __validate(self, token_type):
        if token_type == 'api':
            return self.__validate_api()
        elif token_type == 'lrc':
            return self.__validate_lrc()
        
        return False
    
    def __validate_api(self):
        with open(self.api_tok_file, 'r') as f:
            tok = json.load(f)

        if int(time()) - tok['generated_at'] > tok['expires_in'] or not tok:
            return False
        
        if not self.api_token:
            self.api_token = tok['access_token']
        return True
    
    def __validate_lrc(self):
        with open(self.lrc_tok_file, 'r') as f:
            tok = json.load(f)
        
        if int(time()) > (int(tok['accessTokenExpirationTimestampMs']) / 1000) or not tok:
            return False
        
        if not self.lrc_token:
            self.lrc_token = tok['accessToken']
        return True

    def __search(self, track, artist):
        query = f'{track} artist:{artist}'
        # Search for a song
        headers = {
            'Authorization': f'Bearer {self.api_token}'
        }

        params = {
            'q': query,
            'type': 'track'
        }

        response = requests.get(f"{self.api_ep}/search", headers=headers, params=params)

        if response.status_code != 200:
            raise Exception(f"Failed to get lyrics, error code:{response.status_code}" + response.text)
        
        tracks = response.json()['tracks']['items']

        return tracks