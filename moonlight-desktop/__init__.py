from sys import platform
from os import path
from tempfile import gettempdir
import logging
import traceback

LOG_FILE_PATH = gettempdir() + '/moonlight-desktop.log'

def is_windows():
    return platform in ['Windows', 'win32', 'cygwin']

def is_mac():
    return platform in ['Mac', 'darwin', 'os2', 'os2emx']

def check_argv_for_non_positional_flag(flag, argv):
    value = flag in argv
    if value:
        argv.remove(flag)
    return value

def setup_logger(is_debug=False):
    logger = logging.getLogger('moonlight-desktop')
    logger.setLevel(logging.DEBUG if is_debug else logging.INFO)

    fileHandler = logging.FileHandler(LOG_FILE_PATH)
    fileHandler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(fileHandler)
    logger.addHandler(logging.StreamHandler())

    logger.info('Log file is at {}'.format(LOG_FILE_PATH))

    return logger

def main(argv=None):
    try:
        global logger
        logger = setup_logger(check_argv_for_non_positional_flag('--debug', argv))

        if is_windows():
            from win_app import WinApp
            app = WinApp(argv)
        elif is_mac():
            from mac_app import MacApp
            app = MacApp(argv)
        else:
            raise RuntimeError('Unsupported platform')

        return app.start()
    except Exception as ex:
        from tkinter import Tk, messagebox
        Tk().withdraw()
        stack_trace = "".join(traceback.format_exception(type(ex), ex, ex.__traceback__))
        messagebox.showerror('Moonlight Desktop', '{}\n\n{}'.format(ex, stack_trace))
