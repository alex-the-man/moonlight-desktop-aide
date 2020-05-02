import logging
from PIL import Image

from yaml import safe_load

from pynput import keyboard
from pynput.keyboard import Key, KeyCode

import pystray

logger = logging.getLogger('moonlight-desktop')

def parse_single_key(key_name):
    try:
        key_sets = keyboard.HotKey.parse(key_name)
        if len(key_sets) > 1:
            raise RuntimeError('Please specify only one key, hotkey isn\'t supported: {}'.format(key_name))
        else:
            parsed_key = key_sets.pop()
            if isinstance(parsed_key, Key):
                return parsed_key.value.vk
            else:
                return parsed_key
    except Exception:
        logger.exception('Failed to prase key in config.')
        raise RuntimeError('Invalid key specified: {}'.format(key_name))

class App:
    TARGET_PROCESS = 'Moonlight'

    def __init__(self, log_file_path, argv):
        if '--help' in argv:
            raise RuntimeError('usage: {} [--debug] [config yaml path] [moonlight path]'.format(argv[0]))
        
        self.log_file_path = log_file_path
        self.config_filename = argv[1] if len(argv) > 1 else None
        self.moonlight_path = argv[2] if len(argv) > 2 else None

        self.remap_keys = {}
        self.passthrough_hotkeys = set()
        self.mode = ''

        self.kb_controller = keyboard.Controller()

        self.init_systray()

    def init_systray(self):
        icon = Image.open('icons/systray.png')
        menu_open_log = pystray.MenuItem('View log', lambda: self.open_file_with_associated_app(self.log_file_path))
        menu_quit = pystray.MenuItem('Quit', lambda: self.stop())
        menu = pystray.Menu(menu_open_log, menu_quit)

        self.systray = pystray.Icon('Moonlight Desktop', icon=icon, title='Moonlight Desktop', menu=menu)

    def load_config(self):
        logger.info('Loading config from %s.', self.config_filename)
        with open(self.config_filename, 'r') as config_file:
            config = safe_load(config_file)
            for remap_entry in config.get('remap_keys', {}):
                from_key = parse_single_key(remap_entry['from'])
                to_key = parse_single_key(remap_entry['to'])
                self.remap_keys[from_key] = to_key

            for passthrough_hotkey_string in config.get('passthrough_hotkeys', []):
                passthrough_hotkey = keyboard.HotKey.parse(passthrough_hotkey_string)
                self.passthrough_hotkeys.add(self.pack_hotkey_set_to_tuple(passthrough_hotkey))

            logger.debug('remap_keys: {}'.format(self.remap_keys))
            logger.debug('passthrough_hotkeys: {}'.format(self.passthrough_hotkeys))

            self.mode = config.get('mode')
            if not self.mode in ['server', 'client']: raise RuntimeError('Invalid mode: {}'.format(self.mode))

    def start(self):
        logger.info('Targetting window/application with title/name "%s"', self.TARGET_PROCESS)
        
        self.load_config()

        self.listener = self.create_key_listener()

        try:
            self.listener.start()
            if self.mode == 'client':
                return self.systray.run(lambda systray: self.run_moonlight())
            else:
                self.systray.run()
        finally:
            self.listener.stop()

    def stop(self):
        raise NotImplementedError()
    
    def pack_hotkey_set_to_tuple(self, hotkey_set):
        is_ctrl_down = False
        is_alt_down = False
        is_cmd_down = False
        is_shift_down = False
        main_key = None

        for key in hotkey_set:
            if key == Key.ctrl: is_ctrl_down = True
            elif key == Key.alt: is_alt_down = True
            elif key == Key.cmd: is_cmd_down = True
            elif key == Key.shift: is_shift_down = True
            else:
                if main_key is not None: raise RuntimeError('Only one modifier key in hotkey is allowed: {}'.format(hotkey_set))
                main_key = key

        if main_key is None:
            raise RuntimeError('Cannot find a non modifier key in hotkey: {}'.format(hotkey_set))
        
        if isinstance(main_key, Key):
            main_keycode = main_key.value.vk

        if isinstance(main_key, KeyCode) and main_key.char is not None:
            main_keycode = self.char_to_keycode(main_key.char)
        if main_keycode is None:
            raise RuntimeError('Faild to translate non modifier key to physical key code: {}'.format(main_key))

        return (is_ctrl_down, is_alt_down, is_cmd_down, is_shift_down, main_keycode)

    def open_file_with_associated_app(self, path):
        raise NotImplementedError()
        
    def get_active_window(self):
        raise NotImplementedError()

    def run_moonlight(self):
        raise NotImplementedError()

    def create_key_listener(self):
        raise NotImplementedError()

    def char_to_keycode(self, char):
        raise NotImplementedError()