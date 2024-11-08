import music_tag
import os
import logging

from ext import setup_logger, config, args
from song import Song
from mutagen import MutagenError
from lrc import LrcException
from linux_colors import cprint, Colors

from providers.spotify import Spotify
from providers.lrclib import Lrclib
from providers.musixmatch import Musixmatch

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
    if dump:
        return dump_lyrics(song, lyrics)
    return edit_song_lyrics(song, lyrics)

def dump_lyrics(song: Song, lyrics: str):
    filename = os.path.splitext(song.filepath)[0] + '.lrc'
    with open(filename, 'w') as f:
        f.write(lyrics)

    return True

def edit_song_lyrics(song: Song, lyrics: str):
    try:
        song_file = music_tag.load_file(song.filepath)
        complete_lyrics = f'[00:00.00] {song.title}\n{lyrics}'
        song_file['lyrics'] = complete_lyrics
        song_file.save()
    except Exception as e:
        logging.exception(e)
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
        cprint(f"Processing song {i + 1} / {len(songs)}", Colors.CYAN)
        if song.has_lyrics and not args.overwrite:
            logger.info(song)
            if input('Lyrics already exist, do you want to overwrite? [y/N]: ').lower() != 'y':
                print('Skipping song')
                continue
        elif song.has_lyrics and args.overwrite == 'skip':
            print('Skipping song')
            continue
        print(song)
        for prov in order:
            try:
                cprint(f"Fetching lyrics from {prov}", Colors.BLUE)
                lyrics = providers[prov].get_lyrics(song, args.type)

                if prov == 'musixmatch':
                    if lyrics:
                        if save_lyrics(song, lyrics) == True:
                            cprint(f"Lyrics {'overridden' if song.has_lyrics else 'saved'}", Colors.GREEN)
                            lyrics_saved += 1
                            break
                        else:
                            cprint('Failed to save lyrics', Colors.RED)
                    else:
                        cprint('Lyrics not found', Colors.YELLOW)
                
                #!TODO Rewrite spotify and musixmatch getters to use edit distance -> Remove this block
                else:
                    lyrics, affinity, problems = providers[prov].get_lyrics(song, args.type)
                    print('Max affinity score: ', affinity)
                    if problems:
                        cprint(f"Problems: {problems}", Colors.YELLOW)
                    if not args.yes or affinity < 70:
                        if affinity < 70:
                            cprint('The match is not good enough, please check the problems ^', Colors.YELLOW)
                        if input('Do you want to save the lyrics? [y/N]: ').lower() == 'y':
                            if save_lyrics(song, lyrics) == True:
                                cprint(f"Lyrics {'overridden' if song.has_lyrics else 'saved'}", Colors.GREEN)
                                lyrics_saved += 1
                                break
                            else:
                                cprint('Failed to save lyrics', Colors.RED)
                        else:
                            cprint('Lyrics not saved', Colors.YELLOW)
                    else:
                        if save_lyrics(song, lyrics) == True:
                            cprint(f"Lyrics {'overridden' if song.has_lyrics else 'saved'}", Colors.GREEN)
                            lyrics_saved += 1
                            break
                        else:
                            cprint('Failed to save lyrics', Colors.RED)
            except LrcException as e:
                cprint(e, Colors.RED)
            except Exception as e:
                logging.exception(f"Failed to fetch lyrics: {e}")
    cprint(f"{lyrics_saved} lyrics saved out of {len(songs)} songs", Colors.GREEN)

