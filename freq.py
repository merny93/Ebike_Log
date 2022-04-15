from sqlite3 import Time
from subprocess import call
import time
from threading import Timer
class RepeatedTimer(object):
    '''Stolen from 
    https://stackoverflow.com/a/38317060
    '''
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False
import bisect


from collections import deque
try:
    import RPi.GPIO as GPIO
except:
    import warnings
    warnings.warn("Did not load GPIO running fake data")
    '''This is to test on a computer that doesnt have RPI'''
    class GPIO_FAKE:
        IN = None
        RISING = None
        def setup(self, *args, **kwargs):
            pass
        def add_event_detect(*args, **kwargs):
            rt = RepeatedTimer(0.02,kwargs["callback"])


    GPIO = GPIO_FAKE()

class FreqCounter(object):
    def __init__(self, time_window= 0.1, max_freq = 500) -> None:
        max_len = int(time_window*max_freq)
        self.running_count = deque([], maxlen=max_len)
        self.dt = time_window
    def add_pulse(self):
        self.running_count.append(time.perf_counter())
        # print("jello")
    def freq(self):
        return (len(self.running_count) - bisect.bisect_left(self.running_count, time.perf_counter() - self.dt))/self.dt
    





square_wave_pin = 1

GPIO.setup(square_wave_pin, GPIO.IN)

freq_meter = FreqCounter()




GPIO.add_event_detect(square_wave_pin, GPIO.RISING, callback=freq_meter.add_pulse)


while True:
    time.sleep(1)
    print(freq_meter.freq())