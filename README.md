# SurveyGeocoder
 Generate latitude and longitude from dataset of cities/states/countries with spell checking and entry validation

This script uses the geopy client ([https://github.com/geopy/geopy](https://github.com/geopy/geopy)). Install it with

```shell
pip install geopy
pip install "geopy[aiohttp]"
pip install tqdm
pip install autocorrect
```

By default, a memo file ([memo.csv](memo.csv)) will be created that caches known locations. This can be disabled in [config.json](config.json)