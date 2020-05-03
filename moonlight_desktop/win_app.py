from os import startfile
import logging

from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from win32api import VkKeyScan
from win32con import WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP

from .app import App

logger = logging.getLogger('moonlight-desktop')

class WinApp(App):
    def __init__(self, log_file_path, argv):
        App.__init__(self, log_file_path, 'icons/systray-win.png', argv)

        if self._config_filename is None:
            self._config_filename = 'config/win-server.yaml'

    def start(self):
        self._load_config()

        self._create_key_listener()

        try:
            self._listener.start()
            self.systray.run()
            return 0
        finally:
            self._listener.stop()

    def stop(self):
        self.systray.stop()

    def _create_key_listener(self):
        if len(self._passthrough_hotkeys) > 0: raise NotImplementedError()
        self._listener = keyboard.Listener(
            on_press=None,
            on_release=None,
            suppress=False,
            win32_event_filter=self._win32_key_event_listener)

    def _char_to_keycode(self, char):
        return VkKeyScan(char)

    def _open_file_with_associated_app(self, path):
        startfile(path, 'open')

    def _win32_key_event_listener(self, msg, data):
        is_key_down = msg == WM_KEYDOWN or msg == WM_SYSKEYDOWN
        keycode = data.vkCode
        # logger.debug('vkCode {} {}'.format(data.vkCode, hex(data.vkCode)))

        if keycode in self._remap_keys:
            to = self._remap_keys.get(keycode)
            logger.debug('Remapping {}->{}'.format(keycode, to))
            # Simulate target key.
            self._kb_controller.touch(KeyCode.from_vk(to), is_key_down)
            self._listener.suppress_event()
            return True
        return True
