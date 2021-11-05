# -*- coding: utf-8 -*-
import logging
import xbmcaddon
from resources.lib import script
from resources.lib import kodilogging

kodilogging.config()
logger = logging.getLogger(__name__)

__addon__ = xbmcaddon.Addon("script.trakt-lite")

def Main():
    script.run()

if __name__ == '__main__':
    Main()
