# PodcastDownloader Description
A python script to help download a podcast from an RSS feed

Prerequisites:
```
pip install feedparser, mutagen
```

# Usage
This script can be used in three different ways as noted below.

## Downloading the first X episodes
```
python podcast_downloader.py "rss_feed" -t number_of_podcasts
```

## Downloading a specific episode based on text contained in a title
```
python podcast_downloader.py "rss_feed" -e "text_to_search"
```

## Downloading a specific episode based on its episode number
```
python podcast_downloader.py "rss_feed" -n episode_number
```

## Downloading a range of episodes based on their episode numbers
```
python podcast_downloader.py "rss_feed" -r episode_number_min - episode_number_max
```
