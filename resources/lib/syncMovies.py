# -*- coding: utf-8 -*-

import copy
import logging

from resources.lib import kodiUtilities, utilities

logger = logging.getLogger(__name__)


class SyncMovies():
    def __init__(self, sync, progress):
        self.sync = sync
        if self.sync.show_notification:
            kodiUtilities.notification('%s %s' % (kodiUtilities.getString(
                32045), kodiUtilities.getString(32046)), kodiUtilities.getString(32061))  # Sync started
        if sync.show_progress and not sync.run_silent:
            progress.create("%s %s" % (kodiUtilities.getString(
                32045), kodiUtilities.getString(32046)), "")

        kodiMovies = self.__kodiLoadMovies()
        if not isinstance(kodiMovies, list) and not kodiMovies:
            logger.debug(
                "[Movies Sync] Kodi movie list is empty, aborting movie Sync.")
            if sync.show_progress and not sync.run_silent:
                progress.close()
            return
        try:
            traktMovies = self.__traktLoadMovies()
        except Exception:
            logger.debug(
                "[Movies Sync] Error getting Trakt.tv movie list, aborting movie Sync.")
            if sync.show_progress and not sync.run_silent:
                progress.close()
            return

        self.__addMoviesToTraktWatched(kodiMovies, traktMovies, 59, 69)
        self.__syncMovieRatings(traktMovies, kodiMovies, 92, 99)

        if self.sync.show_progress and not self.sync.run_silent:
            self.sync.UpdateProgress(
                100, line1=kodiUtilities.getString(32066), line2=" ", line3=" ")
            progress.close()

        if self.sync.show_notification:
            kodiUtilities.notification('%s %s' % (kodiUtilities.getString(
                32045), kodiUtilities.getString(32046)), kodiUtilities.getString(32062))  # Sync complete

        logger.debug("[Movies Sync] Movies on Trakt.tv (%d), movies in Kodi (%d)." % (
            len(traktMovies), len(kodiMovies)))
        logger.debug("[Movies Sync] Complete.")

    def __kodiLoadMovies(self):
        self.sync.UpdateProgress(1, line2=kodiUtilities.getString(32079))

        logger.debug("[Movies Sync] Getting movie data from Kodi")
        data = kodiUtilities.kodiJsonRequest({'jsonrpc': '2.0', 'id': 0, 'method': 'VideoLibrary.GetMovies', 'params': {'properties': [
                                             'title', 'imdbnumber', 'uniqueid', 'year', 'playcount', 'lastplayed', 'file', 'dateadded', 'runtime', 'userrating']}})
        if data['limits']['total'] == 0:
            logger.debug("[Movies Sync] Kodi JSON request was empty.")
            return

        kodi_movies = kodiUtilities.kodiRpcToTraktMediaObjects(data)

        self.sync.UpdateProgress(10, line2=kodiUtilities.getString(32080))

        return kodi_movies

    def __traktLoadMovies(self):
        self.sync.UpdateProgress(10, line1=kodiUtilities.getString(
            32079), line2=kodiUtilities.getString(32081))

        logger.debug("[Movies Sync] Getting watched movies from Trakt.tv")

        traktMovies = {}

        self.sync.UpdateProgress(17, line2=kodiUtilities.getString(32082))
        traktMovies = self.sync.traktapi.getMoviesWatched(traktMovies)

        if kodiUtilities.getSettingAsBool('trakt_sync_ratings'):
            traktMovies = self.sync.traktapi.getMoviesRated(traktMovies)

        traktMovies = list(traktMovies.items())

        self.sync.UpdateProgress(24, line2=kodiUtilities.getString(32083))
        movies = []
        for _, movie in traktMovies:
            movie = movie.to_dict()

            movies.append(movie)

        return movies

    def __addMoviesToTraktWatched(self, kodiMovies, traktMovies, fromPercent, toPercent):
        if kodiUtilities.getSettingAsBool('trakt_movie_playcount') and not self.sync.IsCanceled():
            updateTraktTraktMovies = copy.deepcopy(traktMovies)
            updateTraktKodiMovies = copy.deepcopy(kodiMovies)

            traktMoviesToUpdate = utilities.compareMovies(
                updateTraktKodiMovies, updateTraktTraktMovies, kodiUtilities.getSettingAsBool("scrobble_fallback"), watched=True)
            utilities.sanitizeMovies(traktMoviesToUpdate)

            if len(traktMoviesToUpdate) == 0:
                self.sync.UpdateProgress(
                    toPercent, line2=kodiUtilities.getString(32086))
                logger.debug(
                    "[Movies Sync] Trakt.tv movie playcount is up to date")
                return

            titles = ", ".join(["%s" % (m['title'])
                                for m in traktMoviesToUpdate])
            logger.debug("[Movies Sync] %i movie(s) playcount will be updated on Trakt.tv" % len(
                traktMoviesToUpdate))
            logger.debug("[Movies Sync] Movies updated: %s" % titles)

            self.sync.UpdateProgress(fromPercent, line2=kodiUtilities.getString(
                32064) % len(traktMoviesToUpdate))
            # Send request to update playcounts on Trakt.tv
            chunksize = 200
            chunked_movies = utilities.chunks(
                [movie for movie in traktMoviesToUpdate], chunksize)
            errorcount = 0
            i = 0
            x = float(len(traktMoviesToUpdate))
            for chunk in chunked_movies:
                if self.sync.IsCanceled():
                    return
                i += 1
                y = ((i / x) * (toPercent-fromPercent)) + fromPercent
                self.sync.UpdateProgress(int(y), line2=kodiUtilities.getString(
                    32093) % ((i) * chunksize if (i) * chunksize < x else x, x))

                params = {'movies': chunk}
                # logger.debug("moviechunk: %s" % params)
                try:
                    result = self.sync.traktapi.addToHistory(params)
                    logger.debug("[traktUpdateMovies] Movies update result %s" % result)
                except Exception as ex:
                    message = utilities.createError(ex)
                    logging.fatal(message)
                    errorcount += 1

            logger.debug(
                "[Movies Sync] Movies updated: %d error(s)" % errorcount)
            self.sync.UpdateProgress(toPercent, line2=kodiUtilities.getString(
                32087) % len(traktMoviesToUpdate))


    def __syncMovieRatings(self, traktMovies, kodiMovies, fromPercent, toPercent):

        if kodiUtilities.getSettingAsBool('trakt_sync_ratings') and traktMovies and not self.sync.IsCanceled():
            updateKodiTraktMovies = copy.deepcopy(traktMovies)
            updateKodiKodiMovies = copy.deepcopy(kodiMovies)

            traktMoviesToUpdate = utilities.compareMovies(
                updateKodiKodiMovies, updateKodiTraktMovies, kodiUtilities.getSettingAsBool("scrobble_fallback"), rating=True)
            if len(traktMoviesToUpdate) == 0:
                self.sync.UpdateProgress(
                    toPercent, line1='', line2=kodiUtilities.getString(32179))
                logger.debug(
                    "[Movies Sync] Trakt movie ratings are up to date.")
            else:
                logger.debug("[Movies Sync] %i movie(s) ratings will be updated on Trakt" % len(
                    traktMoviesToUpdate))

                self.sync.UpdateProgress(fromPercent, line1='', line2=kodiUtilities.getString(
                    32180) % len(traktMoviesToUpdate))

                moviesRatings = {'movies': traktMoviesToUpdate}

                self.sync.traktapi.addRating(moviesRatings)

