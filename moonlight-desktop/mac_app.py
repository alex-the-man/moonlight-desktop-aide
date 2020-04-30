from os import system, path
import logging

from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from AppKit import NSWorkspace
import Quartz

from app import App

global logger
logger = logging.getLogger('moonlight-desktop')

class MacApp(App):
    def __init__(self, argv):
        App.__init__(self, argv)

        from pynput._util.darwin import get_unicode_to_keycode_map
        self.UNICODE_TO_KEYCODE_MAP = get_unicode_to_keycode_map()

    def get_active_window(self):
        active_window_name = (NSWorkspace.sharedWorkspace().activeApplication()['NSApplicationName'])
        return active_window_name

    def create_key_listener(self):
        return keyboard.Listener(
            on_press=None,
            on_release=None,
            suppress=True,
            darwin_intercept=self.darwin_key_event_listener)

    def run_moonlight(self):
        if self.moonlight_path is None:
            self.moonlight_path = '/Applications/Moonlight.app'

        if not path.isdir(self.moonlight_path):
            logger.error('Cannot find Moonlight at "{}".'.format(self.moonlight_path))
            return 1

        logger.info('Listening for keys until Moonlight quits...')
        exit_code = system('open -W {}'.format(self.moonlight_path))
        logger.info('Moonlight terminated with code %d. Exiting...', exit_code)
        return exit_code

    def darwin_key_event_listener(self, event_type, event):
        try:
            keyboard_type = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeyboardType)
            # Ignore injected keys.
            if keyboard_type == 70:
                return event

            # If Moonlight isn't the active window, don't process.
            if self.get_active_window() != self.TARGET_PROCESS:
                return event

            # Parsing the event.
            flags = Quartz.CGEventGetFlags(event)
            keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)

            # Make sure remapped modifier flags are not leaked along with non-remapped keys.
            filtered_flags = flags & ~(Quartz.kCGEventFlagMaskControl | Quartz.kCGEventFlagMaskAlternate | Quartz.kCGEventFlagMaskCommand)
            Quartz.CGEventSetFlags(event, filtered_flags)

            if event_type == Quartz.kCGEventKeyDown or event_type == Quartz.kCGEventKeyUp:
                return self.darwin_key_press_event(event_type, event, keycode, flags)
            elif event_type == Quartz.kCGEventFlagsChanged:
                return self.darwin_key_flags_changed_event(event, keycode, flags)
        except Exception:
            # Make sure key events are still being passed in error case
            logger.exception('Exception was thrown in the key event listener.')
            return event

    def darwin_key_press_event(self, event_type, event, keycode, flags):
        is_key_down = event_type == Quartz.kCGEventKeyDown
        is_ctrl_down = flags & Quartz.kCGEventFlagMaskControl == Quartz.kCGEventFlagMaskControl
        is_alt_down = flags & Quartz.kCGEventFlagMaskAlternate == Quartz.kCGEventFlagMaskAlternate
        is_cmd_down = flags & Quartz.kCGEventFlagMaskCommand == Quartz.kCGEventFlagMaskCommand
        is_shift_down = flags & Quartz.kCGEventFlagMaskShift == Quartz.kCGEventFlagMaskShift
        key_with_modifiers_tuple = (is_ctrl_down, is_alt_down, is_cmd_down, is_shift_down, keycode)

        # logger.debug('{} {} ctrl: {} alt: {} cmd: {} shift: {}'.format(keycode, 'down' if is_key_down else 'up', is_ctrl_down, is_alt_down, is_cmd_down, is_shift_down))

        # If the key is in the passthrough hotkey list, bypass our modifiers filtering.
        if key_with_modifiers_tuple in self.passthrough_hotkeys:
            logger.debug('Passthrough hotkey: {}'.format(key_with_modifiers_tuple))
            # Simulate modifiers.
            if key_with_modifiers_tuple[0]: self.kb_controller.touch(Key.ctrl, is_key_down)
            if key_with_modifiers_tuple[1]: self.kb_controller.touch(Key.alt, is_key_down)
            if key_with_modifiers_tuple[2]: self.kb_controller.touch(Key.cmd, is_key_down)
            if key_with_modifiers_tuple[3]: self.kb_controller.touch(Key.shift, is_key_down)
            self.kb_controller.touch(KeyCode.from_vk(key_with_modifiers_tuple[4]), is_key_down)
            return None

        return event
            
    def darwin_key_flags_changed_event(self, event, keycode, flags):
        is_ctrl_key = keycode == Key.ctrl.value.vk or keycode == Key.ctrl_l.value.vk or keycode == Key.ctrl_r.value.vk
        is_alt_key = keycode == Key.alt.value.vk or keycode == Key.alt_l.value.vk or keycode == Key.alt_r.value.vk
        is_cmd_key = keycode == Key.alt.value.vk or keycode == Key.cmd_l.value.vk or keycode == Key.cmd_r.value.vk

        is_key_down = None;
        if is_ctrl_key:
            is_key_down = flags & Quartz.kCGEventFlagMaskControl == Quartz.kCGEventFlagMaskControl
        elif is_alt_key:
            is_key_down = flags & Quartz.kCGEventFlagMaskAlternate == Quartz.kCGEventFlagMaskAlternate
        elif is_cmd_key:
            is_key_down = flags & Quartz.kCGEventFlagMaskCommand == Quartz.kCGEventFlagMaskCommand

        # Translate the key
        if not is_key_down is None and keycode in self.remap_keys:
            to = self.remap_keys.get(keycode)
            logger.debug('Remapping {}->{}'.format(keycode, to))
            # Simulate target key.
            self.kb_controller.touch(KeyCode.from_vk(to), is_key_down)
            return None
        return event

    def char_to_keycode(self, char):
        return self.UNICODE_TO_KEYCODE_MAP.get(char)
