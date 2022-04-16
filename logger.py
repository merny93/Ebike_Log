import time
import datetime
from threading import Timer, Thread
import bisect
import os
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

class FreqCounter(object):
    def __init__(self, time_window= 0.1, max_freq = 500, name = "Frequency") -> None:
        max_len = int(time_window*max_freq)
        self.running_count = deque([], maxlen=max_len)
        self.dt = time_window
        self.name = name
    def add_pulse(self):
        self.running_count.append(time.perf_counter())
        # print("jello")
    def __str__(self) -> str:
        return self.name
    def __call__(self):
        return (len(self.running_count) - bisect.bisect_left(self.running_count, time.perf_counter() - self.dt))/self.dt


def file_writer(data, file_name = "UNAMED_DATA.txt"):
    print("Hey saving data")
    with open(os.path.join("data", file_name),"a") as f:
        f.writelines((" ".join((str(val) for val in line)) + "\n" for line in data))


def collect_data(sensors):
    return [time.time()] + [sensor() for sensor in sensors]


CADANCE_PIN= 1
SAMPLE_FREQ = 10
BLOCK_LENGTH = 5
BLOCK_SIZE = int(SAMPLE_FREQ * BLOCK_LENGTH)




# while True:
#     time.sleep(1)
#     print(freq_meter.freq())


try:
    ##set the gpio pin to input
    GPIO.setup(CADANCE_PIN, GPIO.IN)

    ##tell it to count frequency
    freq_meter = FreqCounter()
    GPIO.add_event_detect(CADANCE_PIN, GPIO.RISING, callback=freq_meter.add_pulse)



    sensors = (freq_meter,)

    start_time = time.time()
    n = 0
    data_block = [None] * BLOCK_SIZE
    file_name = datetime.datetime.today().strftime(f"%y-%m-%d_%H:%M:%S") + ".txt"
    with open(os.path.join("data", file_name), "x") as f:
        f.write(" ".join(["Time"] + [str(sensor) for sensor in sensors]) + "\n")

    while True:
        data = collect_data(sensors)
        data_block[n] = data
        n = (n+1) % BLOCK_SIZE
        if n == 0:
            #make a copy of the data
            data_to_save = data_block
            data_block = [None]*BLOCK_SIZE
            #dispatch a thread to save the data
            data_saver_worker = Thread(target=file_writer, args = (data_to_save,), kwargs= {"file_name": file_name })
            data_saver_worker.start()   
            print("saving data at", time.time())
        ## no drift sleep https://stackoverflow.com/a/25251804
        time.sleep(1/SAMPLE_FREQ -  ((time.time() - start_time) % (1/SAMPLE_FREQ)))
except Exception as e:
    warnings.warn(e)
    #catch errors
except KeyboardInterrupt:
    ##normal exit do nothing
    pass
finally:
    print("\nClosing up")
    #do close up

exit()

