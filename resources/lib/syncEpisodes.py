# -*- coding: utf-8 -*-

import copy
from resources.lib import utilities
from resources.lib import kodiUtilities
import logging

logger = logging.getLogger(__name__)

class SyncEpisodes:
    def __init__(self, sync, progress):
        self.sync = sync
        if not self.sync.show_progress and self.sync.sync_on_update and self.sync.notify and self.sync.notify_during_playback:
            kodiUtilities.notification('%s %s' % (kodiUtilities.getString(32045), kodiUtilities.getString(32050)), kodiUtilities.getString(32061))  # Sync started
        if self.sync.show_progress and not self.sync.run_silent:
            progress.create("%s %s" % (kodiUtilities.getString(32045), kodiUtilities.getString(32050)), line1=" ", line2=" ", line3=" ")

        kodiShowsCollected, kodiShowsWatched = self.__kodiLoadShows()
        if not isinstance(kodiShowsCollected, list) and not kodiShowsCollected:
            logger.debug("[Episodes Sync] Kodi collected show list is empty, aborting tv show Sync.")
            if self.sync.show_progress and not self.sync.run_silent:
                progress.close()
            return
        if not isinstance(kodiShowsWatched, list) and not kodiShowsWatched:
            logger.debug("[Episodes Sync] Kodi watched show list is empty, aborting tv show Sync.")
            if self.sync.show_progress and not self.sync.run_silent:
                progress.close()
            return

        traktShowsWatched, traktShowsRated, traktEpisodesRated = self.__traktLoadShows()
        if not traktShowsWatched:
            logger.debug("[Episodes Sync] Error getting Trakt.tv watched show list, aborting tv show sync.")
            if self.sync.show_progress and not self.sync.run_silent:
                progress.close()
            return

        self.__addEpisodesToTraktWatched(kodiShowsWatched, traktShowsWatched, 59, 69)
        self.__syncShowsRatings(traktShowsRated, kodiShowsCollected, 92, 95)
        self.__syncEpisodeRatings(traktEpisodesRated, kodiShowsCollected, 96, 99)

        if not self.sync.show_progress and self.sync.sync_on_update and self.sync.notify and self.sync.notify_during_playback:
            kodiUtilities.notification('%s %s' % (kodiUtilities.getString(32045), kodiUtilities.getString(32050)), kodiUtilities.getString(32062))  # Sync complete

        if self.sync.show_progress and not self.sync.run_silent:
            self.sync.UpdateProgress(100, line1=" ", line2=kodiUtilities.getString(32075), line3=" ")
            progress.close()

        logger.debug("[Episodes Sync] Shows on Trakt.tv (%d), shows in Kodi (%d)." % (len(traktShowsWatched['shows']), len(traktShowsWatched['shows'])))

        logger.debug("[Episodes Sync] Episodes on Trakt.tv (%d), episodes in Kodi (%d)." % (utilities.countEpisodes(traktShowsWatched, collection=False), utilities.countEpisodes(kodiShowsCollected)))
        logger.debug("[Episodes Sync] Complete.")

    ''' begin code for episode sync '''
    def __kodiLoadShows(self):
        self.sync.UpdateProgress(1, line1=kodiUtilities.getString(32094), line2=kodiUtilities.getString(32095))

        logger.debug("[Episodes Sync] Getting show data from Kodi")
        data = kodiUtilities.kodiJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShows', 'params': {'properties': ['title', 'uniqueid', 'year', 'userrating']}, 'id': 0})
        if data['limits']['total'] == 0:
            logger.debug("[Episodes Sync] Kodi json request was empty.")
            return None, None

        tvshows = kodiUtilities.kodiRpcToTraktMediaObjects(data)
        logger.debug("[Episode Sync] Getting shows from kodi finished %s" % tvshows)

        if tvshows is None:
            return None, None
        self.sync.UpdateProgress(2, line2=kodiUtilities.getString(32096))
        resultCollected = {'shows': []}
        resultWatched = {'shows': []}
        i = 0
        x = float(len(tvshows))
        logger.debug("[Episodes Sync] Getting episode data from Kodi")
        for show_col1 in tvshows:
            i += 1
            y = ((i / x) * 8) + 2
            self.sync.UpdateProgress(int(y), line2=kodiUtilities.getString(32097) % (i, x))

            show = {'title': show_col1['title'], 'ids': show_col1['ids'], 'year': show_col1['year'], 'rating': show_col1['rating'],
                    'tvshowid': show_col1['tvshowid'], 'seasons': []}

            data = kodiUtilities.kodiJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodes', 'params': {'tvshowid': show_col1['tvshowid'], 'properties': ['season', 'episode', 'playcount', 'uniqueid', 'lastplayed', 'file', 'dateadded', 'runtime', 'userrating']}, 'id': 0})
            if not data:
                logger.debug("[Episodes Sync] There was a problem getting episode data for '%s', aborting sync." % show['title'])
                return None, None
            elif 'episodes' not in data:
                logger.debug("[Episodes Sync] '%s' has no episodes in Kodi." % show['title'])
                continue

            if 'tvshowid' in show_col1:
                del(show_col1['tvshowid'])

            showWatched = copy.deepcopy(show)
            data2 = copy.deepcopy(data)
            show['seasons'] = kodiUtilities.kodiRpcToTraktMediaObjects(data)

            showWatched['seasons'] = kodiUtilities.kodiRpcToTraktMediaObjects(data2, 'watched')

            resultCollected['shows'].append(show)
            resultWatched['shows'].append(showWatched)

        self.sync.UpdateProgress(10, line2=kodiUtilities.getString(32098))
        return resultCollected, resultWatched

    def __traktLoadShows(self):
        self.sync.UpdateProgress(10, line1=kodiUtilities.getString(32099), line2=kodiUtilities.getString(32100))

        logger.debug('[Episodes Sync] Getting episode watched/rated from Trakt.tv')
        try:
            self.sync.UpdateProgress(12, line2=kodiUtilities.getString(32101))
            traktShowsWatched = {}
            traktShowsWatched = self.sync.traktapi.getShowsWatched(traktShowsWatched)
            traktShowsWatched = list(traktShowsWatched.items())

            traktShowsRated = {}
            traktShowsRated = self.sync.traktapi.getShowsRated(traktShowsRated)
            traktShowsRated = list(traktShowsRated.items())

            traktEpisodesRated = {}
            traktEpisodesRated = self.sync.traktapi.getEpisodesRated(traktEpisodesRated)
            traktEpisodesRated = list(traktEpisodesRated.items())

        except Exception:
            logger.debug("[Episodes Sync] Invalid Trakt.tv show list, possible error getting data from Trakt, aborting Trakt.tv watched/rated update.")
            return False, False, False, False

        i = 0
        x = float(len(traktShowsWatched))
        showsWatched = {'shows': []}
        for _, show in traktShowsWatched:
            i += 1
            y = ((i / x) * 4) + 16
            self.sync.UpdateProgress(int(y), line2=kodiUtilities.getString(32102) % (i, x))

            # will keep the data in python structures - just like the KODI response
            show = show.to_dict()

            showsWatched['shows'].append(show)

        i = 0
        x = float(len(traktShowsRated))
        showsRated = {'shows': []}
        for _, show in traktShowsRated:
            i += 1
            y = ((i / x) * 4) + 20
            self.sync.UpdateProgress(int(y), line2=kodiUtilities.getString(32102) % (i, x))

            # will keep the data in python structures - just like the KODI response
            show = show.to_dict()

            showsRated['shows'].append(show)

        i = 0
        x = float(len(traktEpisodesRated))
        episodesRated = {'shows': []}
        for _, show in traktEpisodesRated:
            i += 1
            y = ((i / x) * 4) + 20
            self.sync.UpdateProgress(int(y), line2=kodiUtilities.getString(32102) % (i, x))

            # will keep the data in python structures - just like the KODI response
            show = show.to_dict()

            episodesRated['shows'].append(show)

        self.sync.UpdateProgress(25, line2=kodiUtilities.getString(32103))

        return showsWatched, showsRated, episodesRated

    def __addEpisodesToTraktWatched(self, kodiShows, traktShows, fromPercent, toPercent):
        if kodiUtilities.getSettingAsBool('trakt_episode_playcount') and not self.sync.IsCanceled():
            updateTraktTraktShows = copy.deepcopy(traktShows)
            updateTraktKodiShows = copy.deepcopy(kodiShows)

            traktShowsUpdate = utilities.compareEpisodes(
                updateTraktKodiShows, updateTraktTraktShows, kodiUtilities.getSettingAsBool("scrobble_fallback"), watched=True)
            utilities.sanitizeShows(traktShowsUpdate)
            # logger.debug("traktShowsUpdate %s" % traktShowsUpdate)

            if len(traktShowsUpdate['shows']) == 0:
                self.sync.UpdateProgress(toPercent, line1=kodiUtilities.getString(32071), line2=kodiUtilities.getString(32106))
                logger.debug("[Episodes Sync] Trakt.tv episode playcounts are up to date.")
                return

            logger.debug("[Episodes Sync] %i show(s) are missing playcounts on Trakt.tv" % len(traktShowsUpdate['shows']))
            for show in traktShowsUpdate['shows']:
                logger.debug("[Episodes Sync] Episodes updated: %s" % self.__getShowAsString(show, short=True))

            self.sync.UpdateProgress(fromPercent, line1=kodiUtilities.getString(32071), line2=kodiUtilities.getString(32070) % (len(traktShowsUpdate['shows'])))
            errorcount = 0
            i = 0
            x = float(len(traktShowsUpdate['shows']))
            for show in traktShowsUpdate['shows']:
                if self.sync.IsCanceled():
                    return
                epCount = utilities.countEpisodes([show])
                title = show['title'].encode('utf-8', 'ignore')
                i += 1
                y = ((i / x) * (toPercent-fromPercent)) + fromPercent
                self.sync.UpdateProgress(int(y), line2=title, line3=kodiUtilities.getString(32073) % epCount)

                s = {'shows': [show]}
                logger.debug("[traktUpdateEpisodes] Shows to update %s" % s)
                try:
                    result = self.sync.traktapi.addToHistory(s)
                    logger.debug("[traktUpdateEpisodes] Show update result %s" % result)
                except Exception as ex:
                    message = utilities.createError(ex)
                    logging.fatal(message)
                    errorcount += 1

            logger.debug("[traktUpdateEpisodes] Finished with %d error(s)" % errorcount)
            self.sync.UpdateProgress(toPercent, line2=kodiUtilities.getString(32072) % (len(traktShowsUpdate['shows'])), line3=" ")

    def __syncShowsRatings(self, traktShows, kodiShows, fromPercent, toPercent):
        if kodiUtilities.getSettingAsBool('trakt_sync_ratings') and traktShows and not self.sync.IsCanceled():
            updateKodiTraktShows = copy.deepcopy(traktShows)
            updateKodiKodiShows = copy.deepcopy(kodiShows)

            traktShowsToUpdate = utilities.compareShows(updateKodiKodiShows, updateKodiTraktShows, kodiUtilities.getSettingAsBool("scrobble_fallback"), rating=True)
            if len(traktShowsToUpdate['shows']) == 0:
                self.sync.UpdateProgress(toPercent, line1='', line2=kodiUtilities.getString(32181))
                logger.debug("[Episodes Sync] Trakt show ratings are up to date.")
            else:
                logger.debug("[Episodes Sync] %i show(s) will have show ratings added on Trakt" % len(traktShowsToUpdate['shows']))

                self.sync.UpdateProgress(fromPercent, line1='', line2=kodiUtilities.getString(32182) % len(traktShowsToUpdate['shows']))

                self.sync.traktapi.addRating(traktShowsToUpdate)

            # needs to be restricted, because we can't add a rating to an episode which is not in our Kodi collection
            kodiShowsUpdate = utilities.compareShows(updateKodiTraktShows, updateKodiKodiShows, kodiUtilities.getSettingAsBool("scrobble_fallback"), rating=True, restrict=True)

            if len(kodiShowsUpdate['shows']) == 0:
                self.sync.UpdateProgress(toPercent, line1='', line2=kodiUtilities.getString(32176))
                logger.debug("[Episodes Sync] Kodi show ratings are up to date.")
            else:
                logger.debug("[Episodes Sync] %i show(s) will have show ratings added in Kodi" % len(kodiShowsUpdate['shows']))

                shows = []
                for show in kodiShowsUpdate['shows']:
                    shows.append({'tvshowid': show['tvshowid'], 'rating': show['rating']})

                # split episode list into chunks of 50
                chunksize = 50
                chunked_episodes = utilities.chunks([{"jsonrpc": "2.0", "id": i, "method": "VideoLibrary.SetTVShowDetails",
                                        "params": {"tvshowid": shows[i]['tvshowid'],
                                                   "userrating": shows[i]['rating']}} for i in range(len(shows))],
                                        chunksize)
                i = 0
                x = float(len(shows))
                for chunk in chunked_episodes:
                    if self.sync.IsCanceled():
                        return
                    i += 1
                    y = ((i / x) * (toPercent-fromPercent)) + fromPercent
                    self.sync.UpdateProgress(int(y), line1='', line2=kodiUtilities.getString(32177) % ((i) * chunksize if (i) * chunksize < x else x, x))

                    kodiUtilities.kodiJsonRequest(chunk)

                self.sync.UpdateProgress(toPercent, line2=kodiUtilities.getString(32178) % len(shows))


    def __syncEpisodeRatings(self, traktShows, kodiShows, fromPercent, toPercent):
        if kodiUtilities.getSettingAsBool('trakt_sync_ratings') and traktShows and not self.sync.IsCanceled():
            updateKodiTraktShows = copy.deepcopy(traktShows)
            updateKodiKodiShows = copy.deepcopy(kodiShows)

            traktShowsToUpdate = utilities.compareEpisodes(
                updateKodiKodiShows, updateKodiTraktShows, kodiUtilities.getSettingAsBool("scrobble_fallback"), rating=True)
            if len(traktShowsToUpdate['shows']) == 0:
                self.sync.UpdateProgress(toPercent, line1='', line2=kodiUtilities.getString(32181))
                logger.debug("[Episodes Sync] Trakt episode ratings are up to date.")
            else:
                logger.debug("[Episodes Sync] %i show(s) will have episode ratings added on Trakt" % len(traktShowsToUpdate['shows']))

                self.sync.UpdateProgress(fromPercent, line1='', line2=kodiUtilities.getString(32182) % len(traktShowsToUpdate['shows']))
                self.sync.traktapi.addRating(traktShowsToUpdate)


    def __getShowAsString(self, show, short=False):
        p = []
        if 'seasons' in show:
            for season in show['seasons']:
                s = ""
                if short:
                    s = ", ".join(["S%02dE%02d" % (season['number'], i['number']) for i in season['episodes']])
                else:
                    episodes = ", ".join([str(i) for i in show['shows']['seasons'][season]])
                    s = "Season: %d, Episodes: %s" % (season, episodes)
                p.append(s)
        else:
            p = ["All"]
        if 'tvdb' in show['ids']:
            return "%s [tvdb: %s] - %s" % (show['title'], show['ids']['tvdb'], ", ".join(p))
        else:
            return "%s [tvdb: No id] - %s" % (show['title'], ", ".join(p))

