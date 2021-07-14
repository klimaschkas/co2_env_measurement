# CO2 Measurement

This repository holds code for a hardware setup to display the current CO2 concentration
in the air, including a graph over the recent hours.

Code is still in construction.

Hardware setup will also be provided.

1) Setup RaspberryPi
2) Connect according to connection layout (TODO)
3) Boot and sudo apt-get update && sudo apt-get upgrade
4) sudo apt-get install fonts-open-sans
5) Enable I2C, SPI and Serial Port
6) Reboot
7) sudo pip3 install -r requirements.txt
8) sudo python3 main.py

or with docker

7) curl -sSL https://get.docker.com | sh

### Setup and initialize co2 sensor
 
1) Put outside for at least 30min while running measurements
2) After 30min, execute the following script:
```python
import mh_z19
mh_z19.detection_range_5000()
mh_z19.abc_off()
mh_z19.zero_point_calibration()
```
This will enable the sensor to measure up to 5000ppm (2000ppm or 10000ppm are also possible),
disables automatic calibration and makes a zero point calibration,
where the zero point equals the atmospheric co2 ppm levels. Therefore, before the zero point
calibration, it has to placed outside for at least 30min to ensure atmospheric 
co2 ppm levels.
---

Author: Simon Klimaschka

