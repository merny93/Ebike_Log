import time
import datetime
from threading import Timer, Thread
import bisect
import os
from collections import deque
import serial

'''ADD UDEV RULE INTO /etc/udev/rules.d
ACTION=="add", ATTRS{idProduct}=="7523", ATTRS{idVendor}=="1a86", MODE="0666"
'''
ser = serial.Serial(
port='/dev/ttyUSB0',
baudrate=115200,
bytesize=serial.EIGHTBITS,
parity=serial.PARITY_NONE,
stopbits=serial.STOPBITS_ONE,
xonxoff=1,
timeout=1
)



try:
    import RPi.GPIO as GPIO
except:
    import warnings
    warnings.warn("Did not load GPIO running fake data")
    '''This is to test on a computer that doesnt have RPI'''
    class GPIO_FAKE:
        IN = None
        RISING = None
        cleanup = lambda self: None
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

class VoltageReader(object):
    def __init__(self, serial_object = ser, channel_number = 0, name = "Voltage"):
        self.name = name
        self.chan_n = channel_number
        self.ser = serial_object
        self.data = [float("Nan")] * 10
        reader_thread = Thread(target=self.get_serial, daemon=True)
        reader_thread.start()
    def get_serial(self):
        while True:
            try:
                data_set = [None] *10
                for i in range(10):
                    data_set[i] = float(self.ser.readline().decode('utf-8').split()[-1][:-1])
                ser.readline()
            except:
                warnings.warn("failed to read serial")
                data_set = [float("Nan")] * 10
            finally:
                self.data = data_set
    def __str__(self):
        return self.name
    def __call__(self):
        return self.data[self.chan_n]

def file_writer(data, file_name = "UNAMED_DATA.txt"):
    with open(os.path.join("data", file_name),"a") as f:
        f.writelines((" ".join((str(val) for val in line)) + "\n" for line in data))


def collect_data(sensors):
    return [time.time()] + [sensor() for sensor in sensors]


CADANCE_PIN= 1
SAMPLE_FREQ = 10
BLOCK_LENGTH = 10
BLOCK_SIZE = int(SAMPLE_FREQ * BLOCK_LENGTH)


try:
    ##set the gpio pin to input
    GPIO.setup(CADANCE_PIN, GPIO.IN)

    ##tell it to count frequency
    freq_meter = FreqCounter()
    GPIO.add_event_detect(CADANCE_PIN, GPIO.RISING, callback=freq_meter.add_pulse)

    #init the voltage meter
    volt_meter = VoltageReader()


    sensors = (freq_meter,volt_meter)

    start_time = time.time()
    n = 0
    data_block = [None] * BLOCK_SIZE
    file_name = datetime.datetime.today().strftime(f"%y-%m-%d_%H:%M:%S") + ".txt"
    print("Writing to file:", file_name)
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
    GPIO.cleanup()
    #do close up

exit()

