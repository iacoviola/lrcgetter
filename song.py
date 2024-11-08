import music_tag
import re

class Song:
    def __init__(self, title: str = None, artist: str = None, album: str = None, 
                 duration: int = None, filepath: str = None):
        self.title = title
        self.artist = artist
        self.album = album
        self.duration = duration
        self.has_lyrics = False
        if filepath:
            self.__load_song_data(filepath)
            self.filepath = filepath

    def __load_song_data(self, filepath: str):
        audiofile = music_tag.load_file(filepath)
        self.title = audiofile['title'].value.replace("’", "'")

        self.title = re.sub(r'\([^)]*\)', '', self.title).strip()

        self.artist = audiofile['artist'].value.replace("’", "'")
        self.album = audiofile['album'].value.replace("’", "'")
        
        self.album = re.sub(r"deluxe .*$", "deluxe", self.album, flags=re.IGNORECASE)
        self.album = re.sub(r"EP", "", self.album, flags=re.IGNORECASE)
        
        self.duration = audiofile['#length'].value

        self.has_lyrics = self.__check_lyrics(audiofile)

    def __check_lyrics(self, audiofile):
        if audiofile['lyrics'].value is not None and len(audiofile['lyrics'].value) > 0:
            if not audiofile['lyrics'].value.startswith("[offset"):
                return True
        return False

    def __str__(self):
        return f"Song details {{\n\ttitle: {self.title}\n\tartist: {self.artist}\n\talbum: {self.album}\n\tduration: {self.duration}\n}}"