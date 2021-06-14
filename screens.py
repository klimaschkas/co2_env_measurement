import math
import time
from collections import deque

import digitalio
import board
import adafruit_rgb_display.st7789 as st7789
from PIL import Image, ImageDraw, ImageFont
from ping3 import ping
import io
import matplotlib.pyplot as plt
import numpy as np
from tasks import CO2ReaderTask


class Screen:
    def __init__(self):
        self.reset_pin = digitalio.DigitalInOut(board.D27)
        self.cs_pin = digitalio.DigitalInOut(board.CE0)
        self.dc_pin = digitalio.DigitalInOut(board.D25)
        self.BAUDRATE = 24000000
        self.spi = board.SPI()
        self.disp = st7789.ST7789(self.spi, height=240, y_offset=80, rotation=180, cs=self.cs_pin, dc=self.dc_pin,
                                  rst=self.reset_pin, baudrate=self.BAUDRATE)
        self.image = Image.new("RGB", (240, 240))
        self.draw = ImageDraw.Draw(self.image)
        # fonts_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
        self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/open-sans/OpenSans-Light.ttf", 14)
        self.font_middle = ImageFont.truetype("/usr/share/fonts/truetype/open-sans/OpenSans-Light.ttf", 24)
        self.font_big = ImageFont.truetype("/usr/share/fonts/truetype/open-sans/OpenSans-Light.ttf", 40)

        self.pages = list()
        self.current_page = 0

    def add_pages(self, pages: list):
        for page in pages:
            self.pages.append(page)

    def main_loop(self):
        render_time_deque = deque(maxlen=50)
        fps_loop_counter = 0
        while True:
            time_start = time.time()
            self.image = Image.new("RGB", (240, 240))
            self.draw = ImageDraw.Draw(self.image)
            self.pages[self.current_page].draw_frame()
            render_time_deque.append(time.time() - time_start)
            if fps_loop_counter == 50:
                fps_loop_counter = 0
                print(f"Avg. FPS: {1 / np.average(render_time_deque)}")
            fps_loop_counter += 1


class Page:
    def __init__(self, screen: Screen, tasks: dict):
        self.screen = screen
        self.tasks = tasks
        self.screensaver = False

    def draw_frame(self):
        pass


class Page_CO2Main(Page):
    def __init__(self, screen: Screen, tasks: dict):
        super().__init__(screen, tasks)
        self.sleep_time = 10

        self.task = CO2ReaderTask(deque_max_length=2500)
        self.previous_co2_measurement_id = 0

    def get_color_for_value(self, ppm_value):
        if ppm_value < 1000:
            return (95, 255, 66)
        elif ppm_value < 1400:
            return (255, 238, 56)
        else:
            return (255, 69, 56)
    
    def draw_frame(self):
        time_start = time.time()
        self.screen.draw.text((0, 0), "ppm CO2", (255, 255, 255), font=self.screen.font_middle)
        self.screen.draw.text((110, 10), f"sleep: {self.sleep_time}s", (255, 255, 255), font=self.screen.font_small)
        self.screen.draw.text((180, 10), f"#: {len(self.tasks['co2'].rolling_measurement_storage)}", (255, 255, 255), font=self.screen.font_small)

        # TODO properly include ping as task
        if self.tasks["ping"].most_recent_measurement:
            self.screen.draw.rectangle(((205, 60), (230, 85)), fill="green")
        else:
            self.screen.draw.rectangle(((205, 60), (230, 85)), fill="red")

        #temp hum
        self.screen.draw.text((0, 220), f"t:{round(self.tasks['temperature'].most_recent_measurement, 1)}°C", (255, 255, 255), font=self.screen.font_small)
        self.screen.draw.text((80, 220), f"h:{round(self.tasks['humidity'].most_recent_measurement, 1)}%", (255, 255, 255), font=self.screen.font_small)

        #co2

        if self.tasks['co2'].counter != self.previous_co2_measurement_id:
            color = (252, 255, 150)
        else:
            color = (255, 255, 255)
        self.screen.draw.text((0, 46), str(self.tasks['co2'].most_recent_measurement) + " ppm", color, font=self.screen.font_big)
        self.previous_co2_measurement_id = self.tasks['co2'].counter
        self.screen.draw.text((180, 220), "serial", (255, 255, 255), font=self.screen.font_small)

        self.screen.draw.rectangle(((0, 40), (240, 42)), fill=self.get_color_for_value(self.tasks['co2'].most_recent_measurement))

        #plot
        self.tasks["plot"].semaphore.acquire()
        if self.tasks["plot"].im is not None:
            self.screen.image.paste(self.tasks["plot"].im, (10, 100))
        self.tasks["plot"].semaphore.release()
        self.screen.disp.image(self.screen.image)


class Page_Screensaver(Page):
    def __init__(self, screen: Screen, tasks: dict):
        super().__init__(screen, tasks)
        
    def draw_frame(self):
        x = 10
        self.screen.draw.rectangle(((0, 0), (240, 240)), fill=(255, 255, 255))
        self.screen.disp.image(self.screen.image)
        time.sleep(0.5)
        self.screen.draw.rectangle(((0, 0), (240, 240)), fill=(255, 0, 0))
        self.screen.disp.image(self.screen.image)
        time.sleep(0.1)
        self.screen.draw.rectangle(((0, 0), (240, 240)), fill=(0, 255, 0))
        self.screen.disp.image(self.screen.image)
        time.sleep(0.1)
        self.screen.draw.rectangle(((0, 0), (240, 240)), fill=(0, 0, 255))
        self.screen.disp.image(self.screen.image)
        time.sleep(0.1)
        for i in range(15):
            self.screen.draw.ellipse((120 - x, 120 - x, 120 + x, 120 + x), fill='white', outline='red')
            self.screen.disp.image(self.screen.image)
            x = int(x ** 1.1)
        for i in range(50):
            for j in range(240):
                brightness = int((math.sin((i + j) / (12 * math.pi / 240)) + 1) * (255 / 4))
                self.screen.draw.rectangle(((j, 0), (j + 1, 240)), fill=(brightness, brightness, brightness))
        self.screen.disp.image(self.screen.image)
