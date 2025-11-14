import threading
from nicegui import ui

style = """
<style>
@import url("https://code.highcharts.com/css/highcharts.css");
@media (prefers-color-scheme: dark) {
    :root {
        /* Colors for data series and points */
        --highcharts-color-0: #b3597c;
        --highcharts-color-1: #c4688c;
        --highcharts-color-2: #78a8d1;
        --highcharts-color-3: #7991d2;
        --highcharts-color-4: #7d7bd4;
        --highcharts-color-5: #977dd5;
        --highcharts-color-6: #b3597c;
        --highcharts-color-7: #b27fd6;

        /* UI colors */
        --highcharts-background-color: none;

        /*
            Neutral color variations
            https://www.highcharts.com/samples/highcharts/css/palette-helper
        */
        --highcharts-neutral-color-100: rgb(255, 255, 255);
        --highcharts-neutral-color-80: rgb(214, 214, 214);
        --highcharts-neutral-color-60: rgb(173, 173, 173);
        --highcharts-neutral-color-40: rgb(133, 133, 133);
        --highcharts-neutral-color-20: rgb(92, 92, 92);
        --highcharts-neutral-color-10: rgb(71, 71, 71);
        --highcharts-neutral-color-5: rgb(61, 61, 61);
        --highcharts-neutral-color-3: rgb(57, 57, 57);

        /* Highlight color variations */
        --highcharts-highlight-color-100: rgb(122, 167, 255);
        --highcharts-highlight-color-80: rgb(108, 144, 214);
        --highcharts-highlight-color-60: rgb(94, 121, 173);
        --highcharts-highlight-color-20: rgb(65, 74, 92);
        --highcharts-highlight-color-10: rgb(58, 63, 71);
    }
}

.highcharts-dark {
    /* Colors for data series and points */
    --highcharts-color-0: #b3597c;
    --highcharts-color-1: #c4688c;
    --highcharts-color-2: #78a8d1;
    --highcharts-color-3: #7991d2;
    --highcharts-color-4: #7d7bd4;
    --highcharts-color-5: #977dd5;
    --highcharts-color-6: #b3597c;
    --highcharts-color-7: #b27fd6;

    /* UI colors */
    --highcharts-background-color: none;

    /* Neutral color variations */
    --highcharts-neutral-color-100: rgb(255, 255, 255);
    --highcharts-neutral-color-80: rgb(214, 214, 214);
    --highcharts-neutral-color-60: rgb(173, 173, 173);
    --highcharts-neutral-color-40: rgb(133, 133, 133);
    --highcharts-neutral-color-20: rgb(92, 92, 92);
    --highcharts-neutral-color-10: rgb(71, 71, 71);
    --highcharts-neutral-color-5: rgb(61, 61, 61);
    --highcharts-neutral-color-3: rgb(57, 57, 57);

    /* Highlight color variations */
    --highcharts-highlight-color-100: rgb(122, 167, 255);
    --highcharts-highlight-color-80: rgb(108, 144, 214);
    --highcharts-highlight-color-60: rgb(94, 121, 173);
    --highcharts-highlight-color-20: rgb(65, 74, 92);
    --highcharts-highlight-color-10: rgb(58, 63, 71);
}
</style>
"""

STATUS_MAPS = {
            'inuse': 'Treadmill Running',
            'paused': 'Paused',
            'walk': 'Walk',
            'idle': 'Treadmill Controller',
            'finished': 'Finished',
        }

THREADS = []
def disown(fn):
    global THREADS
    # Launch new thread
    t = threading.Thread(target=fn)
    THREADS.append(t)
    t.daemon = True
    t.start()

    # Clear out old threads
    THREADS = [thread for thread in THREADS if thread.is_alive()]

class UI:
    def __init__(self, service):
        self.ui = ui
        self.setup()
        self.service = service

        self._state_running = True

    def on_grade_change(self, e):
        disown( lambda *a: self.service.grade_change(e.value) )

    def on_speed_change(self, e):
        disown( lambda *a: self.service.speed_change(e.value) )

    def on_press_go(self):
        disown( self.service.go_start )

    def on_press_stop(self):
        disown( self.service.go_stop )

    def on_run_walk_button(self):
        """ Handles when the run or walk button is pressed
        """
        if self._state_running:
            self._walk_run_button.props("icon=directions_run")
            self._walk_run_button.text = 'Run'
            disown( self.service.go_walk )
        else:
            self._walk_run_button.props("icon=directions_walk")
            self._walk_run_button.text = 'Walk'
            disown( self.service.go_run )
        self._state_running = not self._state_running

    def generate_speed_delta(self, delta):
        return lambda *a: self.service.nudge_speed(delta)

    def generate_grade_delta(self, delta):
        return lambda *a: self.service.nudge_grade(delta)

    def update_status(self, status):
        self._title_label.text = STATUS_MAPS.get(status) or status
        self._title_label.update()

    def update_speed(self, new_value):
        self._speed_display.value = new_value
        self._speed_display.update()

    def update_grade(self, new_value):
        self._grade_display.value = new_value
        self._grade_display.update()

    def update_elapsed(self, elapsed):
        minutes = int(elapsed / 60)
        seconds = elapsed - minutes * 60
        elapsed_text = f"{minutes:02d}:{seconds:05.02f}"
        self._elapsed_label.text = elapsed_text
        self._elapsed_label.update()

    def hiit_show(self):
        if not self._hiit_label.visible:
            self._hiit_label.visible = True

    def hiit_hide(self):
        if self._hiit_label.visible:
            self._hiit_label.visible = False

    def hiit_update_elapsed(self, elapsed:float):
        minutes = int(elapsed / 60)
        seconds = elapsed - minutes * 60
        elapsed_text = f"{minutes:02d}:{seconds:05.02f}"
        self._hiit_label.text = elapsed_text
        self._hiit_label.update()

    def hiit_pulse(self):
        self.service.go_hiit(
            speed=8.0,
            duration=60.0,
        )

    def on_hiit_pulse(self):
        disown( self.hiit_pulse )

    def setting_1(self):
        self.service.grade_change(15)
        self.service.speed_change(3.5)

    def setting_2(self):
        self.service.grade_change(15)
        self.service.speed_change(5)

    def setup(self):
        ui.add_head_html(style)

        with ui.card().tight():
            self._title_label = ui.label("Treadmill Controller").style('font-size: 200%; font-weight: 300; text-align: center')

            '''
            chart = ui.chart({
                'title': False,
                'chart': {'type': 'spline'},
                'yAxis': {
                    'title': {
                        'text': ''
                    },
                },
                'xAxis': {
                    'categories': ['A', 'B']
                },
                'series': [
                    {'name': 'Speed', 'data': [0.1, 0.2]},
                    {'name': 'Incline', 'data': [0.3, 0.4]},
                ],
            }).classes('w-full h-64 highcharts-dashboards-dark')
            '''

            # Now let's include the action buttons bar
            with ui.card_section():
                with ui.row().classes('pt-3 m-auto'):
                    with ui.column().classes('items-stretch'):
                        ui.button('Go', icon='play_arrow', on_click=self.on_press_go)
                    with ui.column().classes('items-stretch'):
                        self._walk_run_button = ui.button('Walk',
                                                    icon='directions_walk',
                                                    on_click=self.on_run_walk_button)
                    with ui.column().classes('items-stretch'):
                        ui.button('Stop', icon='stop', on_click=self.on_press_stop)

                with ui.row().classes('pt-3 m-auto'):
                    with ui.column().classes('items-stretch'):
                        ui.button(
                            'Normal',
                            icon='looks_one',
                            on_click=self.setting_1,
                        )

                    with ui.column().classes('items-stretch'):
                        ui.button(
                            'HIT IT',
                            icon='keyboard_double_arrow_right',
                            on_click=self.on_hiit_pulse,
                        )

                    with ui.column().classes('items-stretch'):
                        ui.button(
                            'Fast',
                            icon='looks_two',
                            on_click=self.setting_2,
                        )

            # Main part allowing changes to grade and speed
            with ui.card_section():
                with ui.row():
                    with ui.column().classes('items-stretch'):
                        self._elapsed_label = ui.label("00:00.00")\
                                             .classes('text-6xl font-mono')
                        self._hiit_label = ui.label("00:00.00") \
                                             .classes('text-6xl font-mono') \
                                             .style("color: #ff2222")
                        self._hiit_label.visible = False

            with ui.card_section():
                with ui.row():
                    with ui.column().classes('items-stretch'):
                        self._grade_display = ui.number(
                                label='INCLINE',
                                value=0.0,
                                format='%.1f',
                                on_change=self.on_grade_change
                            )
                        ui.button('Up +', icon="keyboard_double_arrow_up",
                                on_click=self.generate_grade_delta(1.0))
                        ui.button('Up', icon="arrow_upward",
                                on_click=self.generate_grade_delta(0.5))
                        ui.button('Down', icon="south",
                                on_click=self.generate_grade_delta(-0.5))
                        ui.button('Down +', icon="keyboard_double_arrow_down",
                                on_click=self.generate_grade_delta(-1.0))

                    with ui.column().classes('items-stretch'):
                        self._speed_display = ui.number(
                                label='SPEED',
                                value=0.0,
                                format='%.1f',
                                on_change=self.on_speed_change,
                            )
                        ui.button('Up +', icon="keyboard_double_arrow_up",
                                on_click=self.generate_speed_delta(1.0))
                        ui.button('Up', icon="arrow_upward",
                                on_click=self.generate_speed_delta(0.1))
                        ui.button('Down', icon="south",
                                on_click=self.generate_speed_delta(-0.1))
                        ui.button('Down +', icon="keyboard_double_arrow_down",
                                on_click=self.generate_speed_delta(-1.0))

        dark = ui.dark_mode()
        dark.enable()

    def run(self):
        ui.run(reload=False)


