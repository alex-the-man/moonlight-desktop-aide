from os import system
import logging

from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from win32gui import GetForegroundWindow, GetWindowText
from win32api import VkKeyScan
from win32con import WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP

from app import App

global logger
logger = logging.getLogger('moonlight-desktop')

class WinApp(App):
    def get_active_window(self):
        window = GetForegroundWindow()
        return GetWindowText(window)

    def run_moonlight(self):
        raise NotImplementedError()

    def create_key_listener(self):
        if len(self.passthrough_hotkeys) > 0: raise NotImplementedError()
        return keyboard.Listener(
            on_press=None,
            on_release=None,
            suppress=False,
            win32_event_filter=self.win32_key_event_listener)

    def char_to_keycode(self, char):
        return VkKeyScan(char)

    def win32_key_event_listener(self, msg, data):
        is_key_down = msg == WM_KEYDOWN or msg == WM_SYSKEYDOWN
        keycode = data.vkCode
        # logger.debug('vkCode {} {}'.format(data.vkCode, hex(data.vkCode)))

        if keycode in self.remap_keys:
            to = self.remap_keys.get(keycode)
            logger.debug('Remapping {}->{}'.format(keycode, to))
            # Simulate target key.
            self.kb_controller.touch(KeyCode.from_vk(to), is_key_down)
            self.listener.suppress_event()
            return True
        return True
