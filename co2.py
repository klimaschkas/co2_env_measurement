import digitalio
import board
from PIL import Image, ImageDraw, ImageFont
import PIL.ImageOps
import adafruit_rgb_display.st7789 as st7789
import os
import mh_z19
import matplotlib.pyplot as plt
import numpy as np
import io
from collections import deque
import time
import Adafruit_DHT
import RPi.GPIO as GPIO
from ping3 import ping
import math
import pickle

plt.rcParams['axes.facecolor'] = 'black'
plt.rcParams['axes.labelcolor'] = 'white'
plt.rcParams['xtick.color'] = 'white'
plt.rcParams['ytick.color'] = 'white'
#print(plt.rcParams)

reset_pin = digitalio.DigitalInOut(board.D27)
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
BAUDRATE = 24000000
sleep_time = 10
maxlen_storage = 2400
first_run = True

spi = board.SPI()
disp = st7789.ST7789(spi, height=240, y_offset=80, rotation=180, cs=cs_pin, dc=dc_pin, rst=reset_pin, baudrate=BAUDRATE)
rolling_co2_storage = deque(maxlen=maxlen_storage)

screensaver_counter = 0
first_start = 1

def get_color_for_value(ppm_value):
	if ppm_value < 1000:
		return (95, 255, 66)
	elif ppm_value < 1400:
		return (255, 238, 56)
	else:
		return (255, 69, 56)

while True:
	if first_run:
		if os.path.isfile("deque_store.pickle"):
			with open("deque_store.pickle", "rb") as f:
				rolling_co2_storage = pickle.load(f)
	t1 = time.time()
	image = Image.new("RGB", (240, 240))
	draw = ImageDraw.Draw(image)
	#fonts_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
	font_small = ImageFont.truetype("/usr/share/fonts/truetype/open-sans/OpenSans-Light.ttf", 14)
	font_middle = ImageFont.truetype("/usr/share/fonts/truetype/open-sans/OpenSans-Light.ttf", 24)
	font_big = ImageFont.truetype("/usr/share/fonts/truetype/open-sans/OpenSans-Light.ttf", 40)
	# draw.text((x, y),"Sample Text",(r,g,b))
	draw.text((0, 0),"ppm CO2",(255,255,255),font=font_middle)
	draw.text((110, 10),f"sleep: {sleep_time}s",(255,255,255),font=font_small)
	draw.text((180, 10),f"#: {len(rolling_co2_storage)}",(255,255,255),font=font_small)
	#draw.rectangle(((0, 40), (240, 42)), fill="white")

	if isinstance(ping('192.168.1.102'), float):
		draw.rectangle(((205,60), (230,85)), fill="green")
	else:
		draw.rectangle(((205,60), (230,85)), fill="red")

	sensor = Adafruit_DHT.DHT22
	#GPIO.setmode(GPIO.BOARD)
	GPIO.setup(16, GPIO.IN, pull_up_down = GPIO.PUD_UP)
	humidity, temperature = Adafruit_DHT.read_retry(sensor, 16)
	draw.text((0, 220), f"t:{round(temperature, 1)}°C",(255, 255, 255), font=font_small)
	draw.text((80, 220), f"h:{round(humidity, 1)}%", (255, 255, 255), font=font_small) 
	try:
		measurement = mh_z19.read()['co2']
		if measurement == 500 and len(rolling_co2_storage) == 0:
			pass
		else:
			rolling_co2_storage.append(measurement)
		draw.text((0, 46),str(measurement) + " ppm", (255, 255, 255), font=font_big)
		draw.text((180, 220),"serial",(255,255,255),font=font_small)
		#draw.rectangle(((200, 50), (240, 90)), fill=get_color_for_value(measurement))
	except TypeError:
		measurement = mh_z19.read_from_pwm()['co2']
		if measurement == 500 and len(rolling_co2_storage) == 0:
			pass
		else:
			rolling_co2_storage.append(measurement)
		draw.text((0, 46),str(measurement) + " ppm", (255, 255, 255), font=font_big)
		draw.text((180, 220),"pwm",(255,255,255),font=font_small)
		#draw.rectangle(((200, 50), (240, 90)), fill=get_color_for_value(measurement))
		#draw.text((0, 46),"Init...", (255, 255, 255), font=font_big)

	draw.rectangle(((0, 40), (240, 42)), fill=get_color_for_value(measurement))
	#plt.figure(figsize=(2.3, 1.2), dpi=100, facecolor="black")
	#plt.plot(list(rolling_co2_storage), color="white")
	#plt.gcf().subplots_adjust(left=0.2, bottom=0.17)
	try:
		rolling_co2_diff = np.convolve(a=np.diff(list(rolling_co2_storage)), v=5, mode="same")
	except ValueError:
		print("Skipping diff...")
		rolling_co2_diff = []

	fig, ax1 = plt.subplots(figsize=(2.4, 1.2), dpi=100, facecolor="black")

	color = 'white'
	ax1.plot(rolling_co2_storage, color=color)
	ax1.tick_params(axis='y', labelcolor=color)

	ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

	color = 'tab:blue'
	ax2.plot(rolling_co2_diff, ":", color=color)
	ax2.tick_params(axis='y', labelcolor=color)
	plt.gcf().subplots_adjust(left=0.2, bottom=0.04, right=0.8)
	#fig.tight_layout()  # otherwise the right y-label is slightly clipped

	buf = io.BytesIO()
	plt.savefig(buf, format='png')
	buf.seek(0)
	im = Image.open(buf)

	image.paste(im, (10, 100))

	buf.close()
	plt.close()
	disp.image(image)
	#print(f"Draw took {time.time() - t1}s")
	with open("deque_store.pickle", "wb") as f:
		pickle.dump(rolling_co2_storage, f, pickle.HIGHEST_PROTOCOL)

	screensaver_counter += 1

	if screensaver_counter == 50:
		x = 10
		draw.rectangle(((0,0), (240,240)), fill=(255, 255, 255))
		disp.image(image)
		time.sleep(0.5)
		draw.rectangle(((0,0), (240,240)), fill=(255, 0, 0))
		disp.image(image)
		time.sleep(0.1)
		draw.rectangle(((0,0), (240,240)), fill=(0, 255, 0))
		disp.image(image)
		time.sleep(0.1)
		draw.rectangle(((0,0), (240,240)), fill=(0,0,255))
		disp.image(image)
		time.sleep(0.1)
		for i in range(15):
			draw.ellipse((120 - x, 120 - x, 120 + x, 120 + x), fill = 'white', outline ='red')
			disp.image(image)
			x = int(x ** 1.1)
		for i in range(50):
			for j in range(240):
				brightness = int((math.sin((i+j) / (12 * math.pi / 240)) + 1) * (255/4))
				draw.rectangle(((j,0), (j+1, 240)), fill=(brightness, brightness, brightness))
		disp.image(image)


		screensaver_counter = 0
	else:
		for i in np.arange(0, sleep_time, 0.25):
			#t2 = time.time()
			draw.rectangle(((0, 42), (int((i / sleep_time) * 240), 44)), fill=(255,255,255))
			disp.image(image)
			#print(time.time() - t2)
			#time.sleep(0.1)


	#time.sleep(sleep_time)
