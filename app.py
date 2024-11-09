import logging
import music_tag
import os

from ext import setup_logger, config, args
from linux_colors import cprint, Colors
from lrc import NoTokenException
from mutagen import MutagenError
from song import Song

from providers.lrclib import Lrclib
from providers.musixmatch import Musixmatch
from providers.spotify import Spotify

CLIENT_ID = config.get('KEYS', 'CLIENT_ID')
CLIENT_SECRET = config.get('KEYS', 'CLIENT_SECRET')
SP_DC = config.get('KEYS', 'SP_DC')

setup_logger()

logger = logging.getLogger(__name__)

prov_names = ['lrclib', 'spotify', 'musixmatch']

def songs_from_dir(directory: str):
    songs = []
    for file in os.listdir(directory):
        filepath = os.path.join(directory, file)
        if os.path.isdir(filepath):
            songs.extend(songs_from_dir(filepath))
        elif os.path.isfile(filepath) and file.endswith(('mp3', 'flac', 'm4a')):
            songs.append(Song(filepath=filepath))
    return songs

def songs_from_m3u(filepath: str):
    songs = []
    with open(filepath, 'r') as f:
        for line in f:
            if not line.startswith('#'):
                try:
                    songs.append(Song(filepath=line.strip('\n')))
                except MutagenError as e:
                    logging.exception(e)
    return songs

def save_lyrics(song: Song, lyrics: str, dump=args.dump):
    lyrics = f"[00:00.00] {song.title}\n{lyrics}"
    if dump:
        return dump_lyrics(song, lyrics)
    return edit_song_lyrics(song, lyrics)

def dump_lyrics(song: Song, lyrics: str):
    filename = os.path.splitext(song.filepath)[0] + '.lrc'
    try:
        with open(filename, 'w') as f:
            f.write(lyrics)
    except Exception as e:
        #logging.exception(e)
        return False
    return True

def edit_song_lyrics(song: Song, lyrics: str):
    try:
        song_file = music_tag.load_file(song.filepath)
        song_file['lyrics'] = lyrics
        song_file.save()
    except Exception as e:
        #logging.exception(e)
        return False
    return True

def disambiguate_order(order: str):
    found = []
    order = order.split(',')
    for i, prov in enumerate(order):
        if prov in found:
            raise ValueError(f"Provider {prov} is duplicated")
        match = [name for name in prov_names if name.startswith(prov)]
        if len(match) == 1:
            order[i] = match[0]
            found.append(match[0])
        elif len(match) == 0:
            logger.warning(f"Provider {prov} not found")
            order.pop(i)
        else:
            raise ValueError(f"Provider {prov} is ambiguous")
        
    return order

if __name__ == '__main__':
    songs = []
    providers = {}

    L = Lrclib()
    S = Spotify(CLIENT_ID, CLIENT_SECRET, SP_DC, 'tokens')
    M = Musixmatch('tokens')

    providers['lrclib'] = L
    providers['spotify'] = S
    providers['musixmatch'] = M

    order = disambiguate_order(args.order)

    if os.path.isfile(args.filepath):
        if args.filepath.endswith(('m3u', 'm3u8')):
            songs = songs_from_m3u(args.filepath)
        else:
            songs.append(Song(filepath=args.filepath))
    else:
        songs = songs_from_dir(args.filepath)

    lyrics_saved = 0
    for i, song in enumerate(songs):
        cprint(f"\nProcessing song {i + 1} / {len(songs)}", Colors.CYAN)
        print(song)
        if args.interactive:
            logger.info(song)
            if input(f"Continue? {'(Lyrics found)' if song.has_lyrics else ''} [y/N]: ").lower() != 'y':
                print('Skipping song')
                continue
        elif song.has_lyrics and not args.overwrite:
            print('Lyrics already present, skipping')
            continue
        for prov in order:
            try:
                cprint(f"Fetching lyrics from {prov}", Colors.BLUE)
                lyrics = providers[prov].get_lyrics(song, args.type)
                if lyrics:
                    if save_lyrics(song, lyrics):
                        cprint(f"Lyrics {'overridden' if song.has_lyrics else 'saved'}", Colors.GREEN)
                        lyrics_saved += 1
                        break
                    cprint('Failed to save lyrics', Colors.RED)
                else:
                    cprint('Lyrics not found, falling back to next provider', Colors.YELLOW)
            except NoTokenException as e:
                cprint(f"{prov.capitalize()} {e}", Colors.RED)
    cprint(f"{lyrics_saved} lyrics saved out of {len(songs)} songs", Colors.GREEN)

