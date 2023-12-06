import json
import logging
import shutil

class Memo:
    known_names = None | list[str]
    known_osm_ids = None | list[int]
    map_name = None | dict
    locations = None | dict
    unknown = None | dict

    @staticmethod
    def load():
        memo = None
        Memo.backup()
        try:
            with open('memo.json', 'r') as memo_file:
                memo = json.load(memo_file)
                logging.info("memo successfully loaded")
                logging.info(f'Memo : {memo["locations"]}')
        except:
            Memo.writeDefaultJSON()
            try:
                with open('memo.json', 'r') as memo_file:
                    memo = json.load(memo_file)
                    logging.info("memo successfully loaded")
            except:
                logging.error("Could not open newly created memo file")
        
        Memo.known_names = memo["known_names"]
        Memo.known_osm_ids = memo["known_osm_ids"]
        Memo.map_name = memo["map_name"]
        Memo.locations = memo["locations"]
        Memo.unknown = memo["unknown"]

    @staticmethod
    def isUnknown(name:str, agent:str=None):
        if agent is not None:
            if agent not in Memo.unknown:
                return False
            if name in Memo.unknown[agent]:
                return True
            return False
        
        for agent in Memo.unknown:
            if name in Memo.unknown[agent]:
                return True
            
        return False
    
    @staticmethod
    def removeUnknown(name:str):
        for agent in Memo.unknown:
            if name in Memo.unknown[agent]:
                Memo.unknown[agent].remove(name)
    
    @staticmethod
    def getMapID(name:str) -> int | None:
        if name in Memo.map_name:
            map = Memo.map_name[name]
            return map["id"]
        return None

    @staticmethod
    def search(name:str, id:int|None=None) -> dict | None:
        logging.debug(f"Starting Memo search for \"{name}\"")
        
        if name in Memo.known_names:
            logging.debug(f"\"{name}\" is a known name")
            
            str_id = f"{Memo.getMapID(name)}"
            location = Memo.locations[str_id].copy()
            logging.debug(f"Location found for \"{name}\": {location}")
            return location
        if id is None:
            logging.debug(f"Could not find location from \"{name}\" in Memo")
            return None
        
        if id in Memo.known_osm_ids:
            logging.debug(f"{id} is a known OSM ID")
            str_id = f"{id}"
            if str_id in Memo.locations:
                location = Memo.locations[str_id].copy()
                logging.debug(f"Location found for {id}: \"{location}\"")
                return location
            else:
                logging.debug(f"No valid location was found in Memo for {id}. Removing {id} from Memo's known locations")
                Memo.removeLocation(id)
                return None
        logging.debug(f"Could not find location by \"{name}\" or {id} in Memo")
        return None
        
    
    @staticmethod
    def add(name:str, id:int, loc:dict, confidence):
        if name is None or id is None or loc is None:
            return None
        name = name.lower()
        Memo.addKnown(name, id, confidence)
        
        if "display_name" in loc:
            display_name = loc["display_name"].lower()
            if display_name not in Memo.known_names:
                Memo.addKnown(display_name, id, confidence)

        str_id = f"{id}"

        if str_id in Memo.locations:
            logging.debug(f"Location with OSM ID: {id} already exists")
            return Memo.locations[str_id]

        location = Memo.memoFormat(loc)
        Memo.locations[str_id] = location.copy()
        logging.debug(f"New Location ({name}) added to Memo with OSM ID: {id} - {location}")
        return location

    @staticmethod
    def memoFormat(loc:dict):
        logging.debug(f"Formatting location as Memo format: {loc}")
        removed = {}
        to_remove = ["place_id", "licence", "osm_type", "osm_id", "class", "type", "place_rank", "importance", "boundingbox"]
        for remove in to_remove:
            remove_val = loc.pop(remove, None)
            if remove_val is not None:
                removed[remove] = remove_val
        logging.debug(f"Removed keys from location for Memo format: {removed}")
        address = loc.pop("address", None)
        if address is not None:
            loc["city"] = address.pop("city", "NA")
            loc["county"] = address.pop("county", "NA")
            loc["state"] = address.pop("state", "NA")
            loc["country"] = address.pop("country", "NA")
            loc["street"] = address.pop("road", "NA")
            loc["zip"] = address.pop("postcode", "NA")
            loc["building"] = address.pop("building", "NA")
            loc["house_number"] = address.pop("house_number", "NA")
            logging.debug(f"Remaining address values not included in Memo format: {address}")
        if "latitude" not in loc:
            loc["latitude"] = loc.pop("lat")
        if "longitude" not in loc:
            loc["longitude"] = loc.pop("lon")
        logging.debug("Renamed lat and lon keys to latitude and longitude")
        return loc
        

    @staticmethod
    def addKnown(name:str, id:int, confidence:float=0.1):
        name = name.lower()
        if name not in Memo.known_names:
            Memo.known_names.append(name)
            logging.debug(f"\"{name}\" added as a known location name")
        if id not in Memo.known_osm_ids:
            Memo.known_osm_ids.append(id)
            logging.debug(f"{id} added as a known location id")
        if name not in Memo.map_name:
            Memo.map_name[name] = {"id": id, "confidence": confidence}
            logging.debug(f"Added map for \"{name}\" to {id} with confidence: {confidence}")
    
    @staticmethod
    def addUnknown(agent:str, location:str):
        location = location.lower()
        if agent not in Memo.unknown:
            Memo.unknown[agent] = []
        if not Memo.isUnknown(location, agent):
            Memo.unknown[agent].append(location)
            logging.debug(f"\"{location}\" added as an unknown location name for {agent}")

    @staticmethod
    def removeLocation(id:int):
        Memo.known_osm_ids.remove(id)
        str_id = f"{id}"
        del Memo.locations[str_id]

    @staticmethod
    def memoPrint():
        print(Memo.known_names)
        print(Memo.known_osm_ids)
        print(Memo.map_name)
        print(Memo.locations)

    @staticmethod
    def writeDefaultJSON():
        try:
            default_json = json.dumps(Memo.getDefaultMemo(), indent=4)
            with open('memo.json', 'w') as memo_file:
                memo_file.write(default_json)
        except:
            message = "There was an error while trying to create a new memo.json file"
            logging.error(message)
            BufferError(message)
    
    @staticmethod
    def getDefaultMemo():
        return {
            "unknown": {},
            "known_names": [],
            "known_osm_ids": [],
            "map_name": {},
            "locations": {}
        }
    
    @staticmethod
    def backup():
        shutil.copyfile('memo.bak', 'memo.bak.bak')
        logging.debug("Saved a backup of memo.bak in memo.bak.bak")
        shutil.copyfile('memo.json', 'memo.bak')
        logging.debug("Saved a backup of memo.json in memo.bak")

    @staticmethod
    def save():
        data = {
            "unknown": Memo.unknown,
            "known_names": Memo.known_names,
            "known_osm_ids": Memo.known_osm_ids,
            "map_name": Memo.map_name,
            "locations": Memo.locations
        }
        json_data = json.dumps(data, indent=4)
        try:
            with open('memo.json', 'w') as memo_file:
                memo_file.write(json_data)
                logging.info("Successfully saved Memo data to memo.json")
        except:
            logging.error("Could not write Memo data to memo.json")