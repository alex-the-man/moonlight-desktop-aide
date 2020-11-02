from os import system, path
from time import sleep
from threading import Thread
import subprocess
import logging
from psutil import pid_exists

from pynput import keyboard, mouse
from pynput.keyboard import Key, KeyCode
from pynput._util.darwin import get_unicode_to_keycode_map

from AppKit import NSWorkspace, NSRunningApplication
from Foundation import NSAppleScript
import Quartz

from .app import App

MOUSE_CLIP_X_MARGIN = 50
UNICODE_TO_KEYCODE_MAP = get_unicode_to_keycode_map()
MOONLIGHT_BUNDLE_ID = 'com.moonlight-stream.Moonlight'
MOONLIGHT_APP_NAME = 'Moonlight'

logger = logging.getLogger('moonlight-desktop')

def clip(val, min_, max_):
    return min_ if val < min_ else max_ if val > max_ else val

def get_active_app_bundle_id():
    return NSWorkspace.sharedWorkspace().frontmostApplication().bundleIdentifier()

def get_moonlight_window_bounds():
    for window in Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID):
        if window['kCGWindowOwnerName'] == MOONLIGHT_APP_NAME and window['kCGWindowAlpha'] > 0.5:
            bounds = window['kCGWindowBounds']
            if bounds['Height'] > 50:
                # logger.debug(window)
                return window['kCGWindowBounds']
    return None

class MacApp(App):
    def __init__(self, log_file_path, argv):
        App.__init__(self, log_file_path, 'icons/systray-mac.png', argv)

        if self._config_filename is None:
            self._config_filename = 'config/mac-client.yaml'

        self._moonlight_path = argv[2] if len(argv) > 2 else None
        self._injected_keys = set()

    def start(self):
        self._load_config()

        self._create_listeners()

        try:
            self.kb_listener.start()
            self.enable_input_handling = False
            self.update_moonlight_window_bounds_thread = Thread(target=self._update_moonlight_window_bounds_loop, daemon=True)
            self.update_moonlight_window_bounds_thread.start()
            self.systray.run(lambda systray: self._run_moonlight())
            return 0
        finally:
            self.mouse_listener.stop()
            self.kb_listener.stop()

    def stop(self):
        try:
            self.mouse_listener.stop()
            self.kb_listener.stop()
            for app in NSRunningApplication.runningApplicationsWithBundleIdentifier_(MOONLIGHT_BUNDLE_ID):
                count = 0
                pid = app.processIdentifier()
                while count < 30 and pid_exists(pid): # app.isTerminated() is always false.
                    app.forceTerminate()
                    sleep(1)
                    count += 1
        except Exception:
            logger.exception('Failed to stop Moonlight.') 
    
    def _update_moonlight_window_bounds_loop(self):
        # If the window isn't the foremost window, and isn't in full screen mode (y != 0)
        # Don't clip.
        while True:
            enable_input_handling = False
            if get_active_app_bundle_id() == MOONLIGHT_BUNDLE_ID:
                self._bounds = get_moonlight_window_bounds()
                enable_input_handling = self._bounds is not None and self._bounds['Y'] == 0
            # print(self.enable_input_handling)
            self.enable_input_handling = enable_input_handling
            sleep(0.25)

    def _char_to_keycode(self, char):
        return UNICODE_TO_KEYCODE_MAP.get(char)

    def _create_listeners(self):
        self.mouse_listener = mouse.Listener(
            suppress=True,
            darwin_intercept=self._darwin_mouse_event_listener)
        self.kb_listener = keyboard.Listener(
            suppress=True,
            darwin_intercept=self._darwin_key_event_listener)

    def _darwin_mouse_event_listener(self, event_type, event):
        try:
            # If Moonlight isn't the active window, don't process.
            if event_type == Quartz.kCGEventMouseMoved and self.enable_input_handling and self._bounds is not None:
                bounds = self._bounds
                # Clip the mouse to keep it close to the Moonlight window.
                # Extend Moonlight window bounds horizontally.
                min_x = bounds['X']
                max_x = min_x + bounds['Width']
                min_x -= MOUSE_CLIP_X_MARGIN
                max_x += MOUSE_CLIP_X_MARGIN
                min_y = 0
                max_y = bounds['Y'] + bounds['Height']
                (x, y) = Quartz.CGEventGetLocation(event)
                clipped_x = clip(x, min_x, max_x)
                clipped_y = clip(y, min_y, max_y)
                # logger.info('x: [{}, {}] y:[{}, {}]'.format(min_x, max_x, min_y, max_y))
                if x != clipped_x or y != clipped_y:
                    Quartz.CGSetLocalEventsSuppressionInterval(0)
                    Quartz.CGWarpMouseCursorPosition((clipped_x, clipped_y))
                    Quartz.CGSetLocalEventsSuppressionInterval(0.25)
                    
            return event
        except Exception:
            # Make sure mouse events are still being passed in error case
            logger.exception('Exception was thrown in the mouse event listener.')
            return event

    def _darwin_key_event_listener(self, event_type, event):
        try:
            keyboard_type = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeyboardType)
            # Ignore injected keys.
            if keyboard_type == 70:
                return event

            # If Moonlight isn't the active window, don't process.
            if not self.enable_input_handling:
                return event

            # Parsing the event.
            flags = Quartz.CGEventGetFlags(event)
            keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)

            # Make sure remapped modifier flags are not leaked along with non-remapped keys.
            filtered_flags = flags & ~(Quartz.kCGEventFlagMaskControl | Quartz.kCGEventFlagMaskAlternate | Quartz.kCGEventFlagMaskCommand)
            Quartz.CGEventSetFlags(event, filtered_flags)

            if event_type == Quartz.kCGEventKeyDown or event_type == Quartz.kCGEventKeyUp:
                return self._darwin_key_press_event(event_type, event, keycode, flags)
            elif event_type == Quartz.kCGEventFlagsChanged:
                return self._darwin_key_flags_changed_event(event, keycode, flags)
        except Exception:
            # Make sure key events are still being passed in error case
            logger.exception('Exception was thrown in the key event listener.')
            return event
            
    def _darwin_key_flags_changed_event(self, event, keycode, flags):
        is_ctrl_key = keycode == Key.ctrl.value.vk or keycode == Key.ctrl_l.value.vk or keycode == Key.ctrl_r.value.vk
        is_alt_key = keycode == Key.alt.value.vk or keycode == Key.alt_l.value.vk or keycode == Key.alt_r.value.vk
        is_cmd_key = keycode == Key.alt.value.vk or keycode == Key.cmd_l.value.vk or keycode == Key.cmd_r.value.vk

        is_key_down = None
        if is_ctrl_key:
            is_key_down = flags & Quartz.kCGEventFlagMaskControl == Quartz.kCGEventFlagMaskControl
        elif is_alt_key:
            is_key_down = flags & Quartz.kCGEventFlagMaskAlternate == Quartz.kCGEventFlagMaskAlternate
        elif is_cmd_key:
            is_key_down = flags & Quartz.kCGEventFlagMaskCommand == Quartz.kCGEventFlagMaskCommand

        # Translate the key
        if is_key_down is not None and keycode in self._remap_keys:
            to = self._remap_keys.get(keycode)
            logger.debug('Remapping {}->{}'.format(keycode, to))
            # Simulate target key.
            self._kb_controller.touch(KeyCode.from_vk(to), is_key_down)
            if is_key_down:
                self._injected_keys.add(to)
            else:
                self._injected_keys.discard(to)
            return None
        return event

    def _darwin_key_press_event(self, event_type, event, keycode, flags):
        is_key_down = event_type == Quartz.kCGEventKeyDown
        is_ctrl_down = flags & Quartz.kCGEventFlagMaskControl == Quartz.kCGEventFlagMaskControl
        is_alt_down = flags & Quartz.kCGEventFlagMaskAlternate == Quartz.kCGEventFlagMaskAlternate
        is_cmd_down = flags & Quartz.kCGEventFlagMaskCommand == Quartz.kCGEventFlagMaskCommand
        is_shift_down = flags & Quartz.kCGEventFlagMaskShift == Quartz.kCGEventFlagMaskShift
        key_with_modifiers_tuple = (is_ctrl_down, is_alt_down, is_cmd_down, is_shift_down, keycode)

        # logger.debug('{} {} ctrl: {} alt: {} cmd: {} shift: {}'.format(keycode, 'down' if is_key_down else 'up', is_ctrl_down, is_alt_down, is_cmd_down, is_shift_down))

        # If the key is in the passthrough hotkey list, bypass our modifiers filtering.
        if key_with_modifiers_tuple in self._passthrough_hotkeys:
            logger.debug('Passthrough hotkey: {}'.format(key_with_modifiers_tuple))

            # Unpress injected keys
            for injected_key in self._injected_keys:
                self._kb_controller.touch(KeyCode.from_vk(injected_key), False)
            self._injected_keys.clear()
                
            # Simulate modifiers.
            if key_with_modifiers_tuple[0]: self._kb_controller.touch(Key.ctrl, is_key_down)
            if key_with_modifiers_tuple[1]: self._kb_controller.touch(Key.alt, is_key_down)
            if key_with_modifiers_tuple[2]: self._kb_controller.touch(Key.cmd, is_key_down)
            if key_with_modifiers_tuple[3]: self._kb_controller.touch(Key.shift, is_key_down)
            self._kb_controller.touch(KeyCode.from_vk(key_with_modifiers_tuple[4]), is_key_down)
            return None

        return event

    def _open_file_with_associated_app(self, path):
        subprocess.Popen(['open', path])

    def _run_moonlight(self):
        if self._moonlight_path is None:
            self._moonlight_path = '/Applications/Moonlight.app'

        if not path.isdir(self._moonlight_path):
            logger.error('Cannot find Moonlight at "{}".'.format(self._moonlight_path))
            return 1

        self.systray.visible = True
        self.mouse_listener.start()
        logger.info('Listening for key & mouse events until Moonlight quits...')
        exit_code = system('open -W {}'.format(self._moonlight_path))
        logger.info('Moonlight terminated with code %d. Exiting...', exit_code)

        self.systray.stop()

        return exit_code