import evdev
from evdev import InputDevice, categorize, ecodes

DEVICE_NAME = 'HAOBO Technology USB Composite Device Keyboard'

class Keyboard:
    def __init__(self, service):
        self.device = None
        self.service = service

    def find_keyboard(self):
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for device in devices:
            if device.name != DEVICE_NAME:
                continue
            return device.path

    def keyboard_monitor(self):
        device_path = self.find_keyboard()
        self.device = InputDevice(device_path)

        # Exclusive use of the device
        self.device.grab()

        for event in self.device.read_loop():
            if event.type == ecodes.EV_KEY:
                key_event = categorize(event)
                if key_event.keystate == key_event.key_down:
                    print(f"{key_event.keycode} pressed")
                    if key_event.scancode == evdev.ecodes.KEY_DOWN:
                        self.service.nudge_grade(-0.5)
                    elif key_event.scancode == evdev.ecodes.KEY_UP:
                        self.service.nudge_grade(0.5)
                    elif key_event.scancode == evdev.ecodes.KEY_LEFT:
                        self.service.nudge_speed(-0.2)
                    elif key_event.scancode == evdev.ecodes.KEY_RIGHT:
                        self.service.nudge_speed(0.2)
                    elif key_event.scancode == evdev.ecodes.KEY_SELECT:
                        status = self.service.status
                        if status == 'idle':
                            self.service.go_start()
                        elif status == 'running':
                            print("Move to walking")
                            self.service.go_walk()
                        elif status == 'walking':
                            print("Move to running")
                            self.service.go_run()

                    elif key_event.scancode == evdev.ecodes.KEY_PLAYPAUSE:
                        print(f"!!!!! MEDIA PLAYPLAUSE")
                    elif key_event.scancode == evdev.ecodes.KEY_POWER:
                        print(f"!!!!! POWER")

                    elif key_event.scancode == evdev.ecodes.KEY_PREVIOUSSONG:
                        print(f"!!!!! PREVIOUSSONG")
                    elif key_event.scancode == evdev.ecodes.KEY_NEXTSONG:
                        print(f"!!!!! NEXTSONG")


                    elif key_event.scancode == evdev.ecodes.KEY_VOLUMEUP:
                        print(f"!!!!! VOLUMEUP")
                    elif key_event.scancode == evdev.ecodes.KEY_VOLUMEDOWN:
                        print(f"!!!!! VOLUMEDOWN")

                    elif key_event.scancode == evdev.ecodes.KEY_HOMEPAGE:
                        self.service.do_reset()


    def run(self):
        """ Executes the thread that will monitor the keyboard and
            pass on relevant events to the 
        """
        self.keyboard_monitor_thread = threading.Thread(target=self.keyboard_monitor)
        self.keyboard_monitor_thread.daemon = True
        self.keyboard_monitor_thread.start()
