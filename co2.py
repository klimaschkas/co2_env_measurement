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

plt.rcParams['axes.facecolor'] = 'black'
plt.rcParams['axes.labelcolor'] = 'white'
plt.rcParams['xtick.color'] = 'white'
plt.rcParams['ytick.color'] = 'white'
#print(plt.rcParams)

reset_pin = digitalio.DigitalInOut(board.D27)
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
BAUDRATE = 24000000

spi = board.SPI()
disp = st7789.ST7789(spi, height=240, y_offset=80, rotation=180,cs=cs_pin, dc=dc_pin, rst=reset_pin, baudrate=BAUDRATE)
rolling_co2_storage = deque(maxlen=240)

while True:

	image = Image.new("RGB", (240, 240))
	draw = ImageDraw.Draw(image)
	#fonts_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
	font = ImageFont.truetype("/usr/share/fonts/truetype/open-sans/OpenSans-Light.ttf", 32)
	font2 = ImageFont.truetype("/usr/share/fonts/truetype/open-sans/OpenSans-Light.ttf", 45)
	# draw.text((x, y),"Sample Text",(r,g,b))
	draw.text((0, 0),"ppm CO2",(255,255,255),font=font)
	draw.rectangle(((0, 60), (240, 65)), fill="white")
	measurement = mh_z19.read()['co2']
	rolling_co2_storage.append(measurement)
	draw.text((0, 80),str(measurement) + " ppm", (255, 255, 255), font=font2)

	#d = [5,6,6,7,8,9,9,9,9,7,5,5,4,3,2,1,1]

	plt.figure(figsize=(2.3, 0.9), dpi=100, facecolor="black")
	plt.plot(list(rolling_co2_storage), color="white")
	plt.gcf().subplots_adjust(left=0.2)
	buf = io.BytesIO()
	plt.savefig(buf, format='png')
	buf.seek(0)
	im = Image.open(buf)
	#im = PIL.ImageOps.invert(im)

	image.paste(im, (10, 150))

	buf.close()
	plt.close()
	disp.image(image)
	time.sleep(3)
