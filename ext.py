import logging
import logging.config
import argparse
import datetime

from configparser import ConfigParser

import logging.config
from os import chdir

'''
This module contains the shared code for the other modules
In it are initialized the logger and the configuration parser
The arguments parser is also defined here with the following options:
    filepath: Path to the audio file, directory containing audio files or m3u playlist file
    -t, --type: Type of lyrics to fetch (synced, plain)
    -w, --overwrite: Overwrite already present lyrics without asking
    -i, --interactive: Interactive mode (asks for confirmation before fetching lyrics)
    -o, --order: Specify the order of the getters
    -v, --verbose: Verbose output
    -d, --dump: Dump the lyrics to a file instead of embedding them in the audio file
It also moves the working directory to the folder where the script is located
And defines a shorthand for the datetime.now function
'''

chdir('/home/emiliano/Desktop/lrcgetter')

def now(format='%Y-%m-%d'):
    return datetime.datetime.now().strftime(format)

config = ConfigParser()
config.read('config.cfg')

parser = argparse.ArgumentParser(description='Fetch lyrics from lrclib.net')

parser.add_argument('filepath', 
                    help='Path to the audio file, directory containing audio files or m3u playlist file')
parser.add_argument('-t', '--type', 
                    help='Type of lyrics to fetch (synced, plain)', 
                    choices=['synced', 'plain'], 
                    default='synced')
parser.add_argument('-w', '--overwrite', 
                    help='Overwrite already present lyrics without asking', 
                    action='store_true')
parser.add_argument('-i', '--interactive',
                    help='Interactive mode (asks for confirmation before fetching lyrics)',
                    action='store_true')
parser.add_argument('-o', '--order', 
                    help='Specify the order of the getters, (comma separated), you can also shorten the names to any amount of letters (e.g. "s,mus,lr" for "spotify,musixmatch,lrclib")',
                    default='spotify,lrclib,musixmatch')
parser.add_argument('-v', '--verbose',
                    help='Verbose output',
                    action='store_true')
parser.add_argument('-d', '--dump',
                    help='Dump the lyrics to a file instead of embedding them in the audio file',
                    action='store_true')

args = parser.parse_args()

def setup_logger():
    format = '[%(asctime)s]'

    if args.verbose:
        level = logging.DEBUG
        format += '%(levelname)s:%(filename)s:'
    else:
        level = logging.INFO
    format += '%(message)s'

    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': format,
                #'datefmt': '%Y-%m-%d@%H:%M:%S',
                'datefmt': '%H:%M:%S'
            },
        },
        'handlers': {
            'default': {
                'level': level,
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            '': {
                'handlers': ['default'],
                'level': 'DEBUG',
                'propagate': True
            }
        }
    }

    logging.config.dictConfig(logging_config)