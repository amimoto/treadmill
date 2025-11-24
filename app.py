#!/usr/bin/env python

import threading
import psycopg
import psycopg_pool
import serial
import time
import yaml
import os

from box import Box

from app.ui import UI
from app.treadmill import Treadmill
from app.keyboard import Keyboard

PORTS = {}

class Duration:
    def __init__(self, start, end=None, metadata=None):
        self.start = start

class Database:
    def __init__(self, conninfo:str):
        self.pool = psycopg_pool.ConnectionPool(
            conninfo,
            min_size=1,
            max_size=5,
            max_lifetime=1800,
            max_idle=600,
        )

    def run_query(self, sql, params=None, *, retry=True):
        try:
            with self.pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    if cur.description:
                        return cur.fetchall()
                    return None
        except (OperationalError, ConnectionException, AdminShutdown) as e:
            log.warning("DB connection problem: %s", e)
            if retry:
                # pool will have discarded broken conns when they’re returned
                return run_query(sql, params, retry=False)
            raise

    def inject_event(self, speed:float, grade:float):
        """ Injects the new event into the postgres server
        """
        print(f"Saving: {speed}km/h {grade}%")
        self.run_query(
                """
                insert into events
                ( timestamp, speed, grade )
                values
                ( NOW(), %(speed)s, %(grade)s )
                """,
                {
                    "speed": speed,
                    "grade": grade,
                }
            )


class App:
    def __init__(self, port, debug=False):
        # Load the config
        with open("app.conf") as f:
            buf = f.read()
            self.config = Box(yaml.safe_load(buf))

        self.db = Database(self.config.conninfo)

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
        self.last_update_speed = None
        self.last_update_grade = None

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

    def go_hiit(self, speed: int=0.0, duration: float=60.0, end_speed: int=1.0):
        last_status = self.status
        self.treadmill.set_speed(speed)
        self.hiit_end_tic = time.time() + duration
        time.sleep(duration)
        if end_speed > 1.0:
            self.treadmill.set_speed(end_speed)
        else:
            self.treadmill.set_speed(1.0)
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
        iteration = 0

        while True:
            try:
                treadmill_status = None
                with self.transport_lock:
                    treadmill_status = self.treadmill.status()
                    if treadmill_status:
                        self.treadmill_status = treadmill_status

                        self.current_speed = treadmill_status['speed'].value.value / 10
                        self.current_grade = treadmill_status['grade'].value.value / 100

                        if iteration % 5 == 0:
                            if self.last_update_speed != self.current_speed \
                               or self.last_update_grade != self.current_grade:
                                   self.db.inject_event(self.current_speed, self.current_grade)
                                   self.last_update_speed = self.current_speed
                                   self.last_update_grade = self.current_grade

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
                iteration += 1

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


