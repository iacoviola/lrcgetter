import requests
import logging

from providers.getter import Getter
from song import Song

logger = logging.getLogger(__name__)

class Lrclib(Getter):
    def __init__(self):
        self.api_ep = 'https://lrclib.net/api/'

        self.user_agent = 'lyrics_getter_cmd, v0.0.0, (no source link yet)'

    def get_lyrics(self, song, type):
        tracks = self.__get_songs(song)
        track, aff, probs = self._get_chosen_track(tracks, song)

        return track[f"{type}Lyrics"], aff, probs

    def _get_song(self, obj: dict):
        title = obj['trackName']
        artist = obj['artistName']
        album = obj['albumName']
        duration = obj['duration']

        return Song(title, artist, album, duration)

    def __get_songs(self, song: Song):
        params = {
            'track_name': song.title,
            'artist_name': song.artist,
            'album_name': song.album,
            #"duration": song.duration # Add only for get endpoint
        }

        headers = {
            'User-Agent': self.user_agent
        }

        response = requests.get(self.api_ep + "search", params=params, headers=headers)

        logger.debug(response.url)
        if response.status_code != 200:
            raise Exception(f"Failed to get lyrics, error code:{response.status_code}" + response.text)
        
        return response.json()
    