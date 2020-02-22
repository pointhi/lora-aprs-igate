#!/usr/bin/env python3

# lora-aprs-igate is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# lora_python_gateway is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with lora_python_gateway. If not, see < http://www.gnu.org/licenses/ >.
#
# (C) 2020 by Thomas Pointhuber, <thomas.pointhuber@gmx.at>

import configparser
import logging
import time

import digitalio
import board
import busio
import adafruit_rfm9x

from aprslib import IS as APRS_IS
from aprslib.packets.position import PositionReport

logger = logging.getLogger(__name__)


# load config
config = configparser.ConfigParser()
config.read('config.ini')

if 'GENERAL' not in config or 'APRS' not in config or 'LORA' not in config:
    logger.critical('config file requires "GENERAL", "APRS" and "LORA" section!')
    exit(1)


# set logging level
if config['GENERAL'].getboolean('Debug') is True:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)


def create_gateway_announcement():
    gwpos = PositionReport()
    gwpos.latitude = config['APRS'].getfloat('Latitude', fallback=None)
    gwpos.longitude = config['APRS'].getfloat('Longitude', fallback=None)
    gwpos.altitude = config['APRS'].getfloat('Altitude', fallback=None)
    gwpos.fromcall = config['APRS']['Callsign']
    gwpos.tocall = 'APRS,TCPIP*'  # TODO: correct?
    gwpos.comment = config['APRS'].get('Info', '')
    gwpos.symbol = '&'
    gwpos.symbol_table = 'R'
    return gwpos


# connect to APRS iGate
connect_kwargs = {
    'passwd': config['APRS']['Passcode'],
    'host': config['APRS'].get('Host', fallback='rotate.aprs.net'),
    'port': config['APRS'].getint('Port', fallback=14580)
}

AIS = APRS_IS(config['APRS']['Callsign'], **connect_kwargs)
try:
    # Configure LoRA model pins
    CS = digitalio.DigitalInOut(getattr(board, config['LORA'].get("PinCS", "CE0")))
    RESET = digitalio.DigitalInOut(getattr(board, config['LORA'].get("PinReset", "D25")))
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

    # Create LoRa modem connection and configure it
    rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, config['LORA'].getfloat('Frequency', fallback=433.775))
    rfm9x.signal_bandwidth = config['LORA'].getfloat('Bandwidth', fallback=125000)
    rfm9x.spreading_factor = config['LORA'].getint('SpreadingFactor', fallback=12)
    rfm9x.coding_rate = config['LORA'].getint('CodingRate', fallback=5)
    rfm9x.enable_crc = True

    # connect to APRS iGate
    AIS.connect(blocking=True)

    time.sleep(1)

    gwpos = create_gateway_announcement()
    logger.info('Announce Gateway: "%s"', gwpos)
    AIS.sendall(gwpos)  # TODO: announce regularly

    while True:
        packet = rfm9x.receive(timeout=5, keep_listening=True, with_header=True)
        if packet:
            logger.info('Received (raw bytes): %s with RSSI: %d', packet, rfm9x.rssi)

except Exception as e:
    logger.exception(e)
    exit(1)
except KeyboardInterrupt:
    pass
finally:
    logger.info('Close Gateway Application')
    AIS.close()
    exit(0)

"""


# QRG: 433,775 MHz BW: 125 SF 12 CR 4/5
RADIO_FREQ_MHZ = 433.775

CS = digitalio.DigitalInOut(board.CE1)
RESET = digitalio.DigitalInOut(board.D25)
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)

# Apply new modem config settings to the radio to improve its effective range
rfm9x.signal_bandwidth = 125000
rfm9x.coding_rate = 5
rfm9x.spreading_factor = 12
rfm9x.enable_crc = False

while True:
    packet = rfm9x.receive()
    if packet:
        logger.info('Received (raw bytes): {0}'.format(packet))
"""