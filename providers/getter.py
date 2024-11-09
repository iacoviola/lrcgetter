import json
import logging
import re
import requests as req

from rapidfuzz import fuzz
from time import time
from typing import Union, Callable

from song import Song

logger = logging.getLogger(__name__)

class Getter:
    def get_lyrics(self, song: Song, type: str):
        raise NotImplementedError
    
    def _get(self, endpoint: str, params: dict = {}, headers: dict = {}):
        r = req.get(endpoint, params=params, headers=headers)

        if not r.ok:
            #logger.warning(f"Failed to get data from {r.url}: {r.status_code}")
            return None
        
        return r.json()

    def _post(self, endpoint: str, data: dict, headers: dict):
        r = req.post(endpoint, data=data, headers=headers)

        if not r.ok:
            #logger.warning(f"Failed to get data from {r.url}: {r.status_code}")
            return None
        
        return r.json()
    
    # Sort results based on the score produced by calculating the edit distance between the found song and the song to be searched
    # results' "t['name] t['artists']" and query's "song.title song.artist"
    # Using fuzzywuzzy fuzz.token_set_ratio as the score function

    def __similarity(self, a: str, b: str):
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
        if not results:
            return None
        
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
    
    def _find_token(self, token_file):
        try:
            with open(token_file, 'r') as f:
                tok = json.load(f)
        except FileNotFoundError:
            return None

        if int(time()) > tok.get('expires_at', 0):
            return None

        return tok.get('token', None)