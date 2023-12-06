import json
import logging

class Config:
    file_loc = None
    save_loc = None
    location_col_name = None
    geocode_col_name = None
    use_memo = True
    use_autocorrect = False
    memo_save_counter = None
    default_memo_save_counter = None
    initialized = False
    user_agents = None
    current_agent = 0
    geocode_timeout = 15

    @staticmethod
    def load():
        config = None
        if Config.initialized:
            return

        Config.initialized = True
        try:
            with open('config.json') as config_file:
                config = json.load(config_file)
                logging.info("config successfully loaded")
        except:
            message = "Could not find config.json in root of directory. Please make sure it is created and in the correct location. See README.md for more information."
            logging.error(message)
            FileNotFoundError(message)
            return
        
        if config is None:
            return

        Config.current_agent = 0
        config_keys = ["file_loc", "save_loc", "location_col_name", "geocode_col_name", "use_memo", "user_agents", "memo_save_counter", "geocode_timeout", "use_autocorrect"]
        for key in config_keys:
            Config.loadKey(config, key)
        Config.default_memo_save_counter = Config.memo_save_counter
    
    @staticmethod
    def loadKey(config:dict, key:str):
        try:
            getattr(Config, key)
        except:
            logging.warn(f"Unknown key {key}")
            return
        
        if key not in config:
            message = f"{key} key not found in config.json"
            logging.error(message)
            KeyError(message)
        else:
            setattr(Config, key, config[key])
            logging.debug(f"loaded {key} from config.json as \"{getattr(Config, key)}\"")

    @staticmethod
    def getNextUserAgent() -> str | None:
        agent = None
        
        if Config.user_agents is not None and Config.current_agent >= 0:
            agent = Config.user_agents[Config.current_agent]
            Config.current_agent += 1
            if Config.current_agent > len(Config.user_agents)-1:
                Config.current_agent = -1
        return agent

    @staticmethod
    def hasNextAgent() -> bool:
        if Config.user_agents is not None and Config.current_agent >= 0:
            return True
        return False
    
    @staticmethod
    def resetCurrentAgent() -> None:
        Config.current_agent = 0

    @staticmethod
    def getUseMemo() -> bool:
        return Config.use_memo
    @staticmethod
    def getUseAutocorrect() -> bool:
        return Config.use_autocorrect
    @staticmethod
    def getFileLoc() -> str | None:
        return Config.file_loc
    @staticmethod
    def getSaveLoc() -> str | None:
        return Config.save_loc
    @staticmethod
    def getLocationColName() -> str | None:
        return Config.location_col_name
    @staticmethod
    def getGeocodeColName() -> str | None:
        return Config.geocode_col_name
    @staticmethod
    def getGeocodeTimeout() -> int:
        return Config.geocode_timeout
    
    @staticmethod
    def decrementMemoSaveCounter() -> None:
        if Config.memo_save_counter > 0:
            Config.memo_save_counter -= 1
    @staticmethod
    def resetMemoSaveCounter():
        Config.memo_save_counter = Config.default_memo_save_counter
    @staticmethod
    def needsMemoSave():
        if Config.memo_save_counter > 0:
            return False
        return True
    @staticmethod
    def getDefaultMemoSaveCounter() -> int | None:
        return Config.default_memo_save_counter