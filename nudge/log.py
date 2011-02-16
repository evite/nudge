#!/usr/bin/env python
#
# Copyright (C) 2011 Evite LLC

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import sys
import time
import logging
import logging.handlers
try:
    import curses
except:
    curses = None

__all__ = [
    'try_color_logging',
    '_LogFormatter',
]

""" Custom color logging setup for development purposes.
    Your application should consider properly setting up logging
    for nudge like:

    def config_logging():
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(name)-12s: %(levelname)-8s %(message)s'
        )
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)

    You would call such a function without importing nudge.log before
    your application runs.
"""

def try_color_logging():
    """ If curses is available, and this process is running in a tty,
        try to enable color logging.
    """
    color = False
    if curses and sys.stderr.isatty():
        try:
            curses.setupterm()
            if curses.tigetnum("colors") > 0:
                color = True
        except:
            pass
    channel = logging.StreamHandler()
    channel.setFormatter(_LogFormatter(color=color))
    logging.getLogger().addHandler(channel)

class _LogFormatter(logging.Formatter):
    """ Custom logging formatter. Borrowed from tornado
    """
    def __init__(self, color, *args, **kwargs):
        logging.Formatter.__init__(self, *args, **kwargs)
        self._color = color
        if color:
            fg_color = curses.tigetstr("setaf") or curses.tigetstr("setf") or ""
            self._colors = {
                logging.DEBUG: curses.tparm(fg_color, 4), # Blue
                logging.INFO: curses.tparm(fg_color, 2), # Green
                logging.WARNING: curses.tparm(fg_color, 3), # Yellow
                logging.ERROR: curses.tparm(fg_color, 1), # Red
            }
            self._normal = curses.tigetstr("sgr0")
    def format(self, record):
        try:
            record.message = record.getMessage()
        except Exception, e:
            record.message = "Bad message (%r): %r" % (e, record.__dict__)
        record.asctime = time.strftime(
            "%y%m%d %H:%M:%S", self.converter(record.created))
        prefix = '[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d]' % \
            record.__dict__
        if self._color:
            prefix = (self._colors.get(record.levelno, self._normal) +
                      prefix + self._normal)
        formatted = prefix + " " + record.message
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            formatted = formatted.rstrip() + "\n" + record.exc_text
        return formatted.replace("\n", "\n    ")

try_color_logging()

