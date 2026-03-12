# PodcastDownloader Description
A python script to help download a podcast from an RSS feed

# Usage
This script can be used in three different ways as noted below.

## Downloading the top X episodes
'''
python podcast_downloader.py "rss_feed" -t number_of_podcasts
'''

## Downloading a specific episode based on text contained in a title
'''
python podcast_downloader.py "rss_feed" -e "text_to_search"
'''

## Downloading a specific episode based on its episode number
'''
python podcast_downloader.py "rss_feed" -n episode_number
'''
