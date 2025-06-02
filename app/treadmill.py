from csafe import Controller, STATUSES

import RPi.GPIO as GPIO
import time

RESET = 4
ENTER = 5
ONE = 6
OK = 26

def button_handler_init():
    print("RESET BUTTONS")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(ENTER, GPIO.OUT)
    GPIO.output(ENTER, False)
    GPIO.setup(ONE, GPIO.OUT)
    GPIO.output(ONE, False)
    GPIO.setup(OK, GPIO.OUT)
    GPIO.output(OK, False)
    GPIO.setup(RESET, GPIO.OUT)
    GPIO.output(RESET, True)

def press_enter():
    print("PRESS ENTER")
    GPIO.output(ENTER, True)
    time.sleep(0.1)
    GPIO.output(ENTER, False)

def press_one():
    print("PRESS ONE")
    GPIO.output(ONE, True)
    time.sleep(0.1)
    GPIO.output(ONE, False)

def press_ok():
    print("PRESS OK")
    GPIO.output(OK, True)
    time.sleep(0.1)
    GPIO.output(OK, False)

def press_reset():
    GPIO.output(RESET, False)
    time.sleep(0.1)
    GPIO.output(RESET, True)

def enter_user_id():
    time.sleep(0.2)
    press_enter()
    time.sleep(0.5)
    press_one()
    time.sleep(0.5)
    press_ok()
    time.sleep(0.5)

class Treadmill:
    def __init__(self, transport, debug=False):
        self.csafe = Controller(transport, debug=debug, get_packet_iterations=1)

        # To handle the button actions
        button_handler_init()

        # Just for fun
        self.status_string = ''

    def status(self):
        status_data = csafe.get_status()
        print("!!! STATUS:", status_data.status)

    def reset(self):
        """ Resets the treadmill by "hitting" the big red button a couple of times
        """
        self.stop()
        time.sleep(0.25)
        self.stop()

    def stop(self):
        """ Hits the reset button for 0.1s once
        """
        press_reset()

    def set_speed(self, new_speed):
        """ Send the CSAFE command to change the speed of the treadmill
        """
        normalized_new_speed = int(new_speed * 10)
        print(f"New speed is {normalized_new_speed/10} km/hour")
        self.csafe.set_speed(normalized_new_speed, '0.1 km/hour', _wait_response=False)

    def set_grade(self, new_grade):
        """ Send the CSAFE command to change the grade of the treadmill
        """
        normalized_new_grade = int(new_grade * 100)
        print(f"New grade is {normalized_new_grade/100} %")
        self.csafe.set_grade(normalized_new_grade, '0.01 % grade', _wait_response=False)

    def status(self):
        status_message = self.csafe.get_status()
        if not status_message:
            return
        status = status_message.status
        speed = self.csafe.get_speed()
        grade = self.csafe.get_grade()
        status_string = f"{status}: {speed.value} {speed.unit} {grade.value} {grade.unit}"
        if status_string != self.status_string:
            print(status_string)
            self.status_string = status_string
        return {
            'status': status,
            'speed': speed,
            'grade': grade,
        }

    def start(self, update_status):
        update_status('Resetting')
        self.reset()
        time.sleep(5.0)
        update_status('CSAFE Reset')
        self.csafe.reset()
        update_status('Idle')
        self.csafe.go_idle()
        self.csafe.get_packet()

        # Insert our user id
        update_status('User Enter')
        enter_user_id()
        user_id = self.csafe.get_id()
        print(f"!!!! GOT THE user id {user_id}")

        # Then we move the treadmill into the active state
        update_status('Starting')
        time.sleep(0.5)

        self.csafe.go_inuse()



                
