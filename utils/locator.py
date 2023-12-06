import logging
from typing import Any, Coroutine
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import pandas as pd
from tqdm import tqdm
from utils.autocorrect import Correcter

from utils.config import Config
from utils.memo import Memo


class Locator:
    def __init__(self) -> None:
        self.config = Config.load()
        self.user_agent = Config.getNextUserAgent()

        self.memolocated = 0
        self.geolocated = 0
        self.not_located = 0
        
        self._loadGeocode(self.user_agent)
        self._loadLocations()

        if Config.getUseMemo():
            Memo.load()
        if Config.getUseAutocorrect():
            Correcter.load()
    
    def _loadLocations(self):
        self.locations = pd.read_csv(filepath_or_buffer=Config.getFileLoc())
        self.geocoded_locations = pd.DataFrame(data=[], columns=[Config.getLocationColName(), "latitude", "longitude", "state", "country", "city"])

    def _loadGeocode(self, agent:str):
        geolocator = Nominatim(
            user_agent=agent,
        )
        self.geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    def _runNextAgent(self):
        self._resetCounters()
        self.user_agent = Config.getNextUserAgent()
        self._loadGeocode(self.user_agent)
        
        message = f"Starting location searches on {Config.getFileLoc()} with {self.user_agent}"
        logging.info(message)
        print(message)
        
        self.geocoded_locations[[Config.getLocationColName(), "latitude", "longitude", "state", "country", "city"]] = pd.DataFrame.progress_apply(self.locations, axis=1, func=self._locateRow)

        message = f"Finished location searches on {Config.getFileLoc()} with {self.user_agent}\n\tGeolocated {self.geolocated}/{self._getTotalCount()} locations\n\tFound {self.memolocated}/{self._getTotalCount()} locations from memory\n\tUnable to find {self.not_located}/{self._getTotalCount()} locations"
        logging.info(message)
        print(message)

    def _runAllAgents(self):
        while Config.hasNextAgent():
            self._runNextAgent()
            if Config.getUseMemo():
                Memo.save()
                Config.resetMemoSaveCounter()

    def run(self):
        tqdm.pandas()
        Config.resetCurrentAgent()
        
        self._resetCounters()

        if Config.getUseMemo():
            self._runAllAgents()
        else:
            self._runNextAgent()
        
        self.geocoded_locations.to_csv(
            path_or_buf=Config.getSaveLoc()
        )

    def _resetCounters(self):
        self.geolocated = 0
        self.memolocated = 0
    def _getTotalCount(self):
        return self.geolocated + self.memolocated + self.not_located

    def _code(self, location:str, confidence:float):
        logging.debug(f"Starting geocode for \"{location}\" using {self.user_agent}")
        loc = (self.geocode(
                query=location,
                timeout=Config.getGeocodeTimeout(),
                exactly_one=True,
                addressdetails=True
            ))
        if loc is None:
            logging.info(f"[{self.user_agent}] No location was able to be geocoded from search string: \"{location}\"")
            return None
        else:
            self.geolocated += 1
            loc = loc.raw
            logging.info(f"[{self.user_agent}] Location geocoded from search string: \"{location}\"\n\tConfidence: {confidence}")
            if Config.getUseMemo():
                loc = Memo.add(location, loc["osm_id"], loc, confidence)
                Config.decrementMemoSaveCounter()
                return loc

    def _memoSearch(self, location:str) -> tuple[dict|None, bool]:
        loc = None
        if Config.getUseMemo():
            if Memo.isUnknown(location):
                if Memo.isUnknown(location, self.user_agent):
                    logging.debug(f"Location {location} found as an unknown value for {self.user_agent}")
                    return None, False
                else:
                    logging.debug(f"Location {location} not unknown for {self.user_agent}, but is unknown for another agent")
                    return None, True
            else:
                loc = Memo.search(location)
        if loc is not None:
            self.memolocated += 1
        return loc, False

    def _locateRow(self, location:pd.Series):
        return self.locate(location[Config.getLocationColName()])

    def locate(self, location:str) -> pd.Series:
        location = location.lower()
        logging.debug(f"Starting locate attempt for {location}")
        quick_corrected_location, full_corrected_location = location, location
        is_unknown = [False, False, False]
        confidence = 1.0
        # confidence of 

        loc, is_unknown[0] = self._memoSearch(location)
        if is_unknown[0]:
            confidence *= 0.9

        if loc is None:
            loc = self._code(location, confidence)

        # Quick Auto-Correction
        if loc is None and Config.getUseAutocorrect():
            logging.debug(f"Location unable to be found from initial search string\n\tAttempting quick autocorrect on initial search string: \"{location}\"")
            quick_corrected_location = Correcter.quick_correct(location)
            if quick_corrected_location != location:
                confidence *= 0.7
                logging.debug(f"Attempting memo search on quick corrected search string: \"{quick_corrected_location}\"")
                loc, is_unknown[1] = self._memoSearch(quick_corrected_location)
                if is_unknown[1]:
                    confidence *= 0.9
            else:
                logging.debug(f"The autocorrected string is the same as the initial search string. Further lookups will not be performed using this string")
        
        if loc is None:
            logging.debug(f"Location unable to be found in memo with quick corrected search string (\"{quick_corrected_location}\")")
            if quick_corrected_location != location:
                logging.debug(f"Attempting geocode on quick corrected search string: \"{quick_corrected_location}\"")
                loc = self._code(quick_corrected_location, confidence)
            if loc is not None:
                logging.info(f"Location found with autocorrected text\n\tOriginal search string: \"{location}\"\n\tCorrected search string: \"{quick_corrected_location}\"")
                # add the pre-corrected search string as a known location name as well
                Memo.addKnown(location, Memo.map_name[quick_corrected_location], confidence)

        # Full Auto-Correction
        if loc is None and Config.getUseAutocorrect():
            logging.debug(f"No location found for {quick_corrected_location} using {self.user_agent}.\n\tAttempting to fully autocorrect initial search string: \"{location}\"")
            full_corrected_location = Correcter.slow_correct(location)
            if full_corrected_location != location:
                confidence *= 0.7
                logging.debug(f"Attempting memo search on fully corrected search string: \"{full_corrected_location}\"")
                loc, is_unknown[2] = self._memoSearch(full_corrected_location)
                if is_unknown[2]:
                    confidence *= 0.9
            else:
                logging.debug(f"The autocorrected string is the same as the initial search string. Further lookups will not be performed using this string")
        
        if loc is None and Config.getUseAutocorrect():
            logging.debug(f"Location unable to be found in memo with fully autocorrected search string (\"{full_corrected_location}\")")
            if full_corrected_location != location:
                logging.debug(f"Attempting geocode on fully corrected search string: \"{full_corrected_location}\"")
                loc = self._code(full_corrected_location, confidence)
            if loc is not None:
                logging.info(f"Location found with autocorrected text.\n\tOriginal search string: \"{location}\"\n\tCorrected search string: \"{full_corrected_location}\"")
                # add the pre-corrected search strings as known location names as well
                id = Memo.map_name[full_corrected_location]
                Memo.addKnown(location, id, confidence)
                Memo.addKnown(quick_corrected_location, id, confidence)

        # Add / Remove Unknown
        if loc is None:
            if Config.getUseAutocorrect():
                logging.warn(f"No location found for {location} using {self.user_agent} after factoring in autocorrections")
            else:
                logging.warn(f"No location found for {location} using {self.user_agent}")
            if Config.getUseMemo():
                    self.not_located += 1
                    Memo.addUnknown(self.user_agent, location)
                    if quick_corrected_location != location:
                        Memo.addUnknown(self.user_agent, quick_corrected_location)
                    if full_corrected_location != location:
                        Memo.addUnknown(self.user_agent, full_corrected_location)
                    Config.decrementMemoSaveCounter()
        elif Config.getUseMemo() and (is_unknown[0] is True or is_unknown[1] is True or is_unknown[2] is True):
            # if the location/quick_corrected_location/full_corrected_location was previously unknown for any user agent but was found using this user agent, remove it from unknown since it is now known
            if is_unknown[0] is True:
                Memo.removeUnknown(location)
            if is_unknown[1] is True:
                Memo.removeUnknown(quick_corrected_location)
            if is_unknown[2] is True:
                Memo.removeUnknown(full_corrected_location)
            Config.decrementMemoSaveCounter()
        
        # Save Memo if Needed
        if Config.needsMemoSave():
            logging.debug(f"Memo has recorded {Config.getDefaultMemoSaveCounter()} new records and will save to avoid data loss as configured in \'config.json\'")
            Memo.save()
            Config.resetMemoSaveCounter()

        # Return Results
        if loc is None:
            ret = pd.Series((location, "?", "?", "?", "?", "?"))
        else:
            ret = pd.Series((location, loc.pop("latitude", "NA"), loc.pop("longitude", "NA"), loc.pop("state", "NA"), loc.pop("country", "NA"), loc.pop("city", "NA")))
        return ret
