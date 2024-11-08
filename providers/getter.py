import re
import logging
import requests as req
import json

from typing import Union, Callable
from rapidfuzz import fuzz
from time import time

from song import Song
from lrc import NoMatchFoundException, InstrumentalTrackException

logger = logging.getLogger(__name__)

class Getter:
    def get_lyrics(self, song: Song, type: str):
        raise NotImplementedError

    def _get_song(self, obj: dict):
        raise NotImplementedError
    
    def _get(self, endpoint: str, params: dict = {}, headers: dict = {}):
        r = req.get(endpoint, params=params, headers=headers)

        if not r.ok:
            logger.warning(f"Failed to get data from {r.url}: {r.status_code}")
            return None
        
        return r.json()

    def _post(self, endpoint: str, data: dict, headers: dict):
        r = req.post(endpoint, data=data, headers=headers)

        if not r.ok:
            logger.warning(f"Failed to get data from {r.url}: {r.status_code}")
            return None
        
        return r.json()
    
    # Sort results based on the score produced by calculating the edit distance between the found song and the song to be searched
    # results' "t['name] t['artists']" and query's "song.title song.artist"
    # Using fuzzywuzzy fuzz.token_set_ratio as the score function

    def __similarity(self, a: str, b: str):
        #splitter = re.compile(r'(?:feat.)|(?:ft.)|(?:with)|(?:\sx\s(?!([Aa]mbassador)))|(?:\sX\s(?!([Aa]mbassador)))|\s*[&,×+;/·]\s*')
        #splitter = re.compile(r'(?:feat.)|(?:ft.)|(?:with)|(?:\s[xX]\s(?!([Aa]mbassador)))|*[&,×+;/·]*')
        splitter = re.compile(r'(?:feat.)|(?:ft.)|(?:with)|(?:\s[xX]\s(?!([Aa]mbassador)))|\s*[&,×+;\/·]\s*')
        a = splitter.sub('', a.lower())
        b = splitter.sub('', b.lower())

        return fuzz.token_set_ratio(a, b)
    
    def __acceptable_match(self, a: str, b: str, min: int):
        return round(self.__similarity(a, b)) >= min

    def __sort_results(self, results: list, compare_fn, song: str):
        if isinstance(compare_fn, str):
            def compare_fn(t):
                return t[compare_fn]
            
        def sort_fn(t):
            return self.__similarity(compare_fn(t), song)

        return sorted(results, key=sort_fn, reverse=True)

    def _get_best_match(self, results: list, compare_fn: Union[str, Callable[[dict], str]], song: Song, min: int = 70):
        song_str = f"{song.title} {song.artist} {song.album}"

        result = self.__sort_results(results, compare_fn, song_str)
        best_match = result[0]

        compare = (
            best_match[compare_fn] 
            if isinstance(compare_fn, str) 
            else compare_fn(best_match)
        )

        if self.__acceptable_match(song_str, compare, min):
            return best_match
        return None

    #!TODO Rewrite spotify and musixmatch getters to use edit distance -> Remove this method
    def __affinity(self, found: Song, song: Song):
        splitter = re.compile(r'(?:feat.)|(?:ft.)|(?:with)|(?:\s[xX]\s(?!([Aa]mbassador)))|\s*[&,×+;\/·]\s*')

        problems = {}
        affinity = 0
        if song.title.lower() in found.title.lower():
            affinity += 40
        else:
            problems['title'] = {'song': song.title, 'found': found.title}

        s_arts = splitter.split(song.artist.lower())
        f_arts = splitter.split(found.artist.lower())

        ls = len(s_arts)
        lf = len(f_arts)
        art_affinity = 25 / (lf if ls > lf else ls)

        if len(s_arts) == len(f_arts):
            affinity += 10

        affinity += len(set(s_arts) & set(f_arts)) * art_affinity
            
        if affinity > 40 and affinity < 72:
            problems['artist'] = {'song': song.artist, 'found': found.artist}

        if song.album.lower() in found.album.lower():
            affinity += 10
        else:
            problems['album'] = {'song': song.album, 'found': found.album}

        diff_duration = abs(song.duration - found.duration)
        affinity -= diff_duration
        if diff_duration > 2:
            problems['duration'] = {'song': song.duration, 'found': found.duration}

        return affinity, problems
            
    #!TODO Rewrite spotify and musixmatch getters to use edit distance -> Remove this method
    def _get_chosen_track(self, results: list, song: Song):
        max_affinity = -1
        problems = {}
        chosen = None

        for result in results:
            found = self._get_song(result)
            affinity, probs = self.__affinity(found, song)

            if affinity > max_affinity:
                max_affinity = affinity
                chosen = result
                problems = probs

        if chosen is None:
            raise NoMatchFoundException("No match found for: " + song.filepath)
        
        if chosen.get('instrumental', '') == 'true':
            raise InstrumentalTrackException("Instrumental track skipped: " + song.filepath)
        
        return chosen, max_affinity, problems