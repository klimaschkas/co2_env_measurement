import os
import pickle
import threading
import time
from collections import deque
import mh_z19
import Adafruit_DHT
import RPi.GPIO as GPIO
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import io
from ping3 import ping

from PAJ7620U2 import PAJ7620U2


class Task:
    def __init__(self, deque_max_length: int, name: str, sleep_time=5):
        self.sleep_time = sleep_time
        if os.path.isfile(f"deque_store_{name}.pickle"):
            with open(f"deque_store_{name}.pickle", "rb") as f:
                try:
                    self.rolling_measurement_storage = pickle.load(f)
                except:
                    os.remove(f"deque_store_{name}.pickle")
                    self.rolling_measurement_storage = deque(maxlen=deque_max_length)
                # TODO EOFError when pickle file is corrupted, catch!
        else:
            self.rolling_measurement_storage = deque(maxlen=deque_max_length)
        self.name = name
        self.most_recent_measurement = -1
        self.thread = None

    def start_background_thread(self):
        self.thread = threading.Thread(target=self.read_loop)
        self.thread.start()

    def stop_background_thread(self):
        self.thread.raise_exception()
        self.thread.join()

    def read(self):
        pass

    def read_loop(self):
        while True:
            self.read()
            time.sleep(self.sleep_time)


class CO2ReaderTask(Task):
    def __init__(self, deque_max_length, sleep_time=5):
        super().__init__(deque_max_length, "co2", sleep_time=sleep_time)
        # TODO catch a failing co2 read#
        # counter is to distinguish if a new measurement arrived
        self.counter = 0
        self.startup_counter = 5

    def save_measurement(self, measurement):
        self.most_recent_measurement = measurement
        if self.startup_counter > 0:
            self.startup_counter -= 1
        else:
            self.rolling_measurement_storage.append(measurement)
        with open(f"deque_store_{self.name}.pickle", "wb") as f:
            pickle.dump(self.rolling_measurement_storage, f, pickle.HIGHEST_PROTOCOL)
        self.counter += 1
        self.counter = self.counter % 50

    def read(self):
        try:
            measurement = mh_z19.read()['co2']
            self.save_measurement(measurement)
        except TypeError:
            measurement = mh_z19.read_from_pwm()['co2']
            self.save_measurement(measurement)


class TemperatureHumiditySensor:
    def __init__(self, sleep_time=5):
        self.sleep_time = sleep_time

        self.sensor = Adafruit_DHT.DHT22
        GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self.temperature = -1
        self.humidity = -1
        self.thread = None

        self.start_background_thread()

    def make_measurements(self):
        while True:
            self.humidity, self.temperature = Adafruit_DHT.read_retry(self.sensor, 16)
            time.sleep(self.sleep_time)

    def read_sensor(self):
        return self.humidity, self.temperature

    def start_background_thread(self):
        self.thread = threading.Thread(target=self.make_measurements)
        self.thread.start()


class TemperatureReaderTask(Task):
    def __init__(self, deque_max_length, temp_hum_sensor, sleep_time=5):
        super().__init__(deque_max_length, "temp", sleep_time=sleep_time)
        # TODO catch a failing temperature read
        self.temp_hum_sensor = temp_hum_sensor
        self.counter = 0
        self.startup_counter = 5

        self.start_background_thread()

    def save_measurement(self, measurement):
        self.most_recent_measurement = measurement
        if self.startup_counter > 0:
            self.startup_counter -= 1
        else:
            self.rolling_measurement_storage.append(measurement)
        with open(f"deque_store_{self.name}.pickle", "wb") as f:
            pickle.dump(self.rolling_measurement_storage, f, pickle.HIGHEST_PROTOCOL)
        self.counter += 1
        self.counter = self.counter % 50

    def read(self):
        _, temperature = self.temp_hum_sensor.read_sensor()
        self.save_measurement(round(temperature, 1))


class HumidityReaderTask(Task):
    def __init__(self, deque_max_length, temp_hum_sensor, sleep_time=5):
        super().__init__(deque_max_length, "humid", sleep_time=sleep_time)
        # TODO catch a failing humidity read
        self.temp_hum_sensor = temp_hum_sensor

        self.counter = 0
        self.startup_counter = 5

        self.start_background_thread()

    def save_measurement(self, measurement):
        self.most_recent_measurement = measurement
        if self.startup_counter > 0:
            self.startup_counter -= 1
        else:
            self.rolling_measurement_storage.append(measurement)
        with open(f"deque_store_{self.name}.pickle", "wb") as f:
            pickle.dump(self.rolling_measurement_storage, f, pickle.HIGHEST_PROTOCOL)
        self.counter += 1
        self.counter = self.counter % 50

    def read(self):
        humidity, _ = self.temp_hum_sensor.read_sensor()
        self.save_measurement(round(humidity, 1))


class PingReaderTask(Task):
    def __init__(self, deque_max_length: int):
        super().__init__(deque_max_length, "ping")

        self.start_background_thread()
        self.most_recent_measurement = False

    def read(self):
        self.most_recent_measurement = isinstance(ping('192.168.1.102'), float)


class PlotBuilderTask(Task):
    def __init__(self, deque_max_length: int, reader_task: Task, screen):
        super().__init__(deque_max_length, "plot")
        self.reader_task = reader_task
        self.screen = screen
        self.semaphore = threading.Semaphore(value=1)
        self.im = None

        plt.rcParams['axes.facecolor'] = 'black'
        plt.rcParams['axes.labelcolor'] = 'white'
        plt.rcParams['xtick.color'] = 'white'
        plt.rcParams['ytick.color'] = 'white'

        self.start_background_thread()

    def read(self):
        fig, ax1 = plt.subplots(figsize=(2.4, 1.2), dpi=100, facecolor="black")

        color = 'white'
        ax1.plot(self.reader_task.rolling_measurement_storage, color=color)
        ax1.tick_params(axis='y', labelcolor=color)

        ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

        color = 'tab:blue'
        ax2.plot(self.reader_task.rolling_measurement_storage, ":", color=color)
        ax2.tick_params(axis='y', labelcolor=color)
        plt.gcf().subplots_adjust(left=0.2, bottom=0.04, right=0.8)
        # fig.tight_layout()  # otherwise the right y-label is slightly clipped
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        im = Image.open(buf)
        #buf.close()

        #self.screen.disp.image(self.screen.image)

        self.semaphore.acquire()
        self.im = im
        self.semaphore.release()

        plt.close()


class GestureReaderTask(Task):
    def __init__(self, deque_max_length, screen, sleep_time=0.05):
        super().__init__(deque_max_length, "gesture",sleep_time=sleep_time)

        self.screen = screen
        self.paj7620u2 = PAJ7620U2()
        self.start_background_thread()

    def save_measurement(self, measurement):
        self.rolling_measurement_storage.append(measurement)
        self.most_recent_measurement = measurement

    def read(self):
        gesture = self.paj7620u2.get_gesture()
        if gesture == "Up":
            self.screen.enable()
        elif gesture == "Down":
            self.screen.disable()
        elif gesture == "Right":
            self.screen.next_page()
        elif gesture == "Left":
            self.screen.previous_page()
