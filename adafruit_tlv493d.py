# The MIT License (MIT)
#
# Copyright (c) 2019 Bryan Siepert for Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`adafruit_tlv493d`
================================================================================

CircuitPython helper library for the TLV493D 3-axis magnetometer

* Author(s): Bryan Siepert

Implementation Notes
--------------------

**Hardware:**


Adafruit's TLV493D Breakout https://adafruit.com/products


**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

import struct
import adafruit_bus_device.i2c_device as i2cdevice
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_TLV493D.git"

class TLV493D:
    """Driver for the TLV493D 3-axis Magnetometer.

    :param busio.I2C i2c_bus: The I2C bus the TLV493D is connected to.

    """

    read_masks = {
        "BX1": (0, 0xFF, 0),
        "BX2": (4, 0xF0, 4),
        "BY1": (1, 0xFF, 0),
        "BY2": (4, 0x0F, 0),
        "BZ1": (2, 0xFF, 0),
        "BZ2": (5, 0x0F, 0),
        "TEMP1": (3, 0xF0, 4),
        "TEMP2": (6, 0xFF, 0),
        "FRAMECOUNTER": (3, 0x0C, 2),
        "CHANNEL": (3, 0x03, 0),
        "POWERDOWNFLAG": (5, 0x10, 4),
        "RES1": (7, 0x18, 3),
        "RES2": (8, 0xFF, 0),
        "RES3": (9, 0x1F, 0)
    }

    write_masks = {
        "PARITY":(1, 0x80, 7),
        "ADDR":(1, 0x60, 5),
        "INT":(1, 0x04, 2),
        "FAST":(1, 0x02, 1),
        "LOWPOWER":(1, 0x01, 0),
        "TEMP_DISABLE":(3, 0x80, 7),
        "LP_PERIOD":(3, 0x40, 6),
        "POWERDOWN":(3, 0x20, 5),
        "RES1":(1, 0x18, 3),
        "RES2":(2, 0xFF, 0),
        "RES3":(3, 0x1F, 0)
    }

    def __init__(self, i2c_bus):
        self.i2c_device = i2cdevice.I2CDevice(i2c_bus, 0x5E)
        self.read_buffer = bytearray(10)
        self.write_buffer = bytearray(4)

        # read in data from sensor, including data that must be set on a write
        self._setup_write_buffer()

        # setup MASTERCONTROLLEDMODE which takes a measurement for every read
        self._set_write_key('PARITY', 1)
        self._set_write_key('PARITY', 1)
        self._set_write_key('LOWPOWER', 1)
        self._set_write_key('LP_PERIOD', 1)
        self._write_i2c()

    def _read_i2c(self):
        with self.i2c_device as i2c:
            i2c.readinto(self.read_buffer)
        # self.print_bytes(self.read_buffer)

    def _write_i2c(self):
        with self.i2c_device as i2c:
            i2c.write(self.write_buffer)

    def _setup_write_buffer(self):
        self._read_i2c()
        for key in ['RES1', 'RES2', 'RES3']:
            write_value = self._get_read_key(key)
            self._set_write_key(key, write_value)

    def _get_read_key(self, key):
        read_byte_num, read_mask, read_shift = self.read_masks[key]
        raw_read_value = self.read_buffer[read_byte_num]
        write_value = (raw_read_value & read_mask)>>read_shift
        return write_value

    def _set_write_key(self, key, value):
        write_byte_num, write_mask, write_shift = self.write_masks[key]
        current_write_byte = self.write_buffer[write_byte_num]
        current_write_byte &= ~write_mask
        current_write_byte |= value<<write_shift
        self.write_buffer[write_byte_num] = current_write_byte

    @property
    def magnetic(self):
        """The processed magnetometer sensor values.
        A 3-tuple of X, Y, Z axis values in microteslas that are signed floats.
        """
        self._read_i2c() # update read registers
        x_top = self._get_read_key("BX1")
        x_bot = ((self._get_read_key("BX2") << 4) & 0xFF)
        y_top = self._get_read_key("BY1")
        y_bot = ((self._get_read_key("BY2") << 4) & 0xFF)
        z_top = self._get_read_key("BZ1")
        z_bot = ((self._get_read_key("BZ2") << 4) & 0xFF)

        return (self._unpack_and_scale(x_top, x_bot),
                self._unpack_and_scale(y_top, y_bot),
                self._unpack_and_scale(z_top, z_bot))

    def _unpack_and_scale(self, top, bottom): #pylint: disable=no-self-use
        binval = struct.unpack_from(">h", bytearray([top, bottom]))[0]
        binval = binval >>4
        return binval * 0.098
