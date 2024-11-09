import logging
import requests

from providers.getter import Getter
from song import Song

logger = logging.getLogger(__name__)

class Lrclib(Getter):

    API_EP = 'https://lrclib.net/api'
    USER_AGENT = 'lyrics_getter_cmd, v0.0.0, (no source link yet)'

    def get_lyrics(self, song, type):
        tracks = self.__get_songs(song)

        compare = lambda t: f"{t['trackName']} {t['artistName']} {t['albumName']}"
        track = self._get_best_match(tracks, compare, song)

        return track[f"{type}Lyrics"]

    def __get_songs(self, song: Song):
        params = {
            'track_name': song.title,
            'artist_name': song.artist,
            'album_name': song.album,
        }
        headers = { 'User-Agent': self.USER_AGENT }
        url = f"{self.API_EP}/search"

        body = self._get(url, params, headers)

        if not body:
            return None
        return body
    