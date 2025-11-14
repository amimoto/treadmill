#!/usr/bin/env python

import threading
import serial
import time
import os

from app.ui import UI
from app.treadmill import Treadmill
from app.keyboard import Keyboard

PORTS = {}

class Duration:
    def __init__(self, start, end=None, metadata=None):
        self.start = start

class App:
    def __init__(self, port, debug=False):
        # Treadmill driver
        # For the connection to the treadmill
        if port not in PORTS:
            transport = serial.Serial(port, 9600, timeout=0.2)
            transport.transport_lock = threading.Lock()
            PORTS[port] = transport
        self.transport = PORTS[port]
        self.treadmill = Treadmill(transport=self.transport, debug=debug)
        self.transport_lock = transport.transport_lock

        # UI handler
        self.ui = UI(self)

        # Status can be one of
        # - idle
        # - starting
        # - running
        # - walking
        # - manual
        self.status = None
        self.treadmill_status = None
        self.current_speed = None
        self.target_speed = None
        self.current_grade = None
        self.target_grade = None

        self.start_tic = None
        self.hiit_end_tic = None

    def start_elapsed(self):
        self.start_tic = time.time()

    def go_start(self):
        with self.transport_lock:
            self.target_speed = None
            self.target_grade = None
            self.treadmill.start(self.ui.update_status)
            self.start_elapsed()

    def go_walk(self):
        with self.transport_lock:
            self.target_speed = self.current_speed
            self.status = 'walking'
            self.treadmill.set_speed(1)

    def go_run(self):
        with self.transport_lock:
            self.status = 'running'
            self.treadmill.set_speed(self.target_speed)

    def do_reset(self):
        self.treadmill.reset()

    def go_stop(self):
        with self.transport_lock:
            self.treadmill.stop()

    def go_hiit(self, speed: int=0.0, duration: float=60.0):
        current_speed = self.current_speed
        last_status = self.status
        self.treadmill.set_speed(speed)
        self.hiit_end_tic = time.time() + duration
        time.sleep(duration)
        self.treadmill.set_speed(current_speed)
        self.hiit_end_tic = None

    def nudge_speed(self, delta):
        if self.target_speed is None:
            self.target_speed = self.current_speed
        new_speed = self.target_speed + delta
        if new_speed < 1:
            new_speed = 1
        self.target_speed = new_speed
        with self.transport_lock:
            self.treadmill.set_speed(new_speed)

    def nudge_grade(self, delta):
        if self.target_grade is None:
            self.target_grade = self.current_grade
        new_grade = self.target_grade + delta
        if new_grade < 0:
            new_grade = 0
        self.target_grade = new_grade
        with self.transport_lock:
            self.treadmill.set_grade(new_grade)

    def grade_change(self, value):
        if value != self.current_grade:
            self.treadmill.set_grade(value)

    def speed_change(self, value):
        if value != self.current_speed:
            self.treadmill.set_speed(value)

    def treadmill_monitor(self):
        while True:
            try:
                treadmill_status = None
                with self.transport_lock:
                    treadmill_status = self.treadmill.status()
                    if treadmill_status:
                        self.treadmill_status = treadmill_status
                        self.current_speed = treadmill_status['speed'].value.value / 10
                        self.current_grade = treadmill_status['grade'].value.value / 100
                        self.ui.update_speed( self.current_speed )
                        self.ui.update_grade( self.current_grade )
                        status = treadmill_status['status']

                        if status == 'inuse':
                            if self.status not in ['running', 'walking']:
                                self.status = 'running'

                            # Figure out how much time has passed
                            if self.start_tic is not None:
                                current_tic = time.time()
                                elapsed = current_tic - self.start_tic
                                self.ui.update_elapsed(elapsed)

                            # Display the HIIT countdown if it's running
                            if self.hiit_end_tic:
                                self.ui.hiit_show()
                                current_tic = time.time()
                                elapsed = self.hiit_end_tic - current_tic
                                self.ui.hiit_update_elapsed(elapsed)
                            else:
                                self.ui.hiit_hide()

                        elif status in ['idle','ready']:
                            self.status = 'idle'

                        elif status in ['finished', 'manual']:
                            self.status = 'manual'

                        self.ui.update_status( status )

                time.sleep(0.2)

            except Exception as ex:
                print(f"ERROR: {ex} <{treadmill_status}>")
                import traceback
                traceback.print_exc()
                time.sleep(1)

    def run(self):
        self.ui_thread = threading.Thread(target=self.ui.run)
        self.ui_thread.daemon = True
        self.ui_thread.start()

        # Monitoring thread on the treadmill
        self.treadmill_monitor_thread = threading.Thread(target=self.treadmill_monitor)
        self.treadmill_monitor_thread.daemon = True
        self.treadmill_monitor_thread.start()

        # Keyboard Monitoring thread
        keyboard = Keyboard(self)
        self.keyboard_monitor_thread = threading.Thread(target=keyboard.keyboard_monitor)
        self.keyboard_monitor_thread.daemon = True
        self.keyboard_monitor_thread.start()

        while True:
            time.sleep(1)

app = App('/dev/ttyUSB0', debug=False)
app.run()


