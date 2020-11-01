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
    def __init__(self, log_file_path, systray_icon_path, argv):
        if '--help' in argv:
            raise RuntimeError('usage: {} [--debug] [config yaml path] [moonlight path]'.format(argv[0]))
        
        self._log_file_path = log_file_path
        self._config_filename = argv[1] if len(argv) > 1 else None

        self._remap_keys = {}
        self._passthrough_hotkeys = set()

        self._kb_controller = keyboard.Controller()

        self._init_systray(systray_icon_path)

    def _init_systray(self, systray_icon_path):
        icon = Image.open(systray_icon_path)
        menu_open_log = pystray.MenuItem('View log', lambda: self._open_file_with_associated_app(self._log_file_path))
        menu_quit = pystray.MenuItem('Quit', lambda: self.stop())

        menu = self._create_pystray_menu(menu_open_log, menu_quit)

        self.systray = pystray.Icon('Moonlight Desktop', icon=icon, title='Moonlight Desktop', menu=menu)

    def _create_pystray_menu(self, *items):
        return pystray.Menu(*items)

    def _load_config(self):
        logger.info('Loading config from %s.', self._config_filename)
        with open(self._config_filename, 'r') as config_file:
            config = safe_load(config_file)
            for remap_entry in config.get('remap_keys', {}):
                from_key = parse_single_key(remap_entry['from'])
                to_key = parse_single_key(remap_entry['to'])
                self._remap_keys[from_key] = to_key

            for passthrough_hotkey_string in config.get('passthrough_hotkeys', []):
                passthrough_hotkey = keyboard.HotKey.parse(passthrough_hotkey_string)
                self._passthrough_hotkeys.add(self._pack_hotkey_set_to_tuple(passthrough_hotkey))

            logger.debug('remap_keys: {}'.format(self._remap_keys))
            logger.debug('passthrough_hotkeys: {}'.format(self._passthrough_hotkeys))

    def start(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()
    
    def _char_to_keycode(self, char):
        raise NotImplementedError()

    def _open_file_with_associated_app(self, path):
        raise NotImplementedError()

    def _pack_hotkey_set_to_tuple(self, hotkey_set):
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
            main_keycode = self._char_to_keycode(main_key.char)
        if main_keycode is None:
            raise RuntimeError('Faild to translate non modifier key to physical key code: {}'.format(main_key))

        return (is_ctrl_down, is_alt_down, is_cmd_down, is_shift_down, main_keycode)
