import platform

class Colors:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

os = platform.system()
colors = True if os == "Linux" else False

def colorize(text, color):
    return f"{color}{text}{Colors.END if colors else text}"

def cprint(text, color):
    print(colorize(text, color))