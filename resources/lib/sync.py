# -*- coding: utf-8 -*-


import xbmc
import xbmcgui
import logging
from resources.lib import syncEpisodes
from resources.lib import syncMovies
from resources.lib.kodiUtilities import getSettingAsBool

progress = xbmcgui.DialogProgress()
logger = logging.getLogger(__name__)

class Sync():
    def __init__(self, show_progress=False, run_silent=False, library="all", api=None):
        self.traktapi = api
        self.show_progress = show_progress
        self.run_silent = run_silent
        self.library = library
        if self.show_progress and self.run_silent:
            logger.debug("Sync is being run silently.")
        self.sync_on_update = getSettingAsBool('sync_on_update')
        self.notify = getSettingAsBool('show_sync_notifications')
        self.notify_during_playback = not (xbmc.Player().isPlayingVideo() and getSettingAsBool("hide_notifications_playback"))

    def __syncCheck(self, media_type):
        if media_type == 'movies':
            return getSettingAsBool('trakt_movie_playcount')
        else:
            return getSettingAsBool('trakt_episode_playcount')

    def sync(self):
        logger.debug("Starting synchronization with Trakt.tv")
        
        if self.__syncCheck('movies'):
            if self.library in ["all", "movies"]:
                syncMovies.SyncMovies(self, progress)
            else:
                logger.debug("Movie sync is being skipped for this manual sync.")
        else:
            logger.debug("Movie sync is disabled, skipping.")

        if self.__syncCheck('episodes'):
            if self.library in ["all", "episodes"]:
                if not (self.__syncCheck('movies') and self.IsCanceled()):
                    syncEpisodes.SyncEpisodes(self, progress)
                else:
                    logger.debug("Episode sync is being skipped because movie sync was canceled.")
            else:
                logger.debug("Episode sync is being skipped for this manual sync.")
        else:
            logger.debug("Episode sync is disabled, skipping.")

        logger.debug("[Sync] Finished synchronization with Trakt.tv")


    def IsCanceled(self):
        if self.show_progress and not self.run_silent and progress.iscanceled():
            logger.debug("Sync was canceled by user.")
            return True
        else:
            return False

    def UpdateProgress(self, *args, **kwargs):
        if self.show_progress and not self.run_silent:
            kwargs['percent'] = args[0]
            progress.update(**kwargs)