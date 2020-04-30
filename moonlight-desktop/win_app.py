from os import system, path
import logging

from pynput import keyboard
from pynput.keyboard import Key, KeyCode

import Quartz

from app import App

global logger
logger = logging.getLogger('moonlight-desktop')

class WinApp(App):
    def get_active_window(self):
        from win32gui import GetForegroundWindow, GetWindowText

        window = GetForegroundWindow()
        return GetWindowText(window)
    