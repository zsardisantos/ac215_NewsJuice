# news_feed_test

simple prototype for pulling newsfeeds from RSS source

do:

docker build -t news-feed -f Dockerfile .

docker run --rm -ti -v "$(pwd)":/app news-feed

and then in container: 

python news_feed_test.py

possible next steps:
* identify Harvard sources
* other formats of sources (those are RSS feeds only)
* have a file with a list of sources that is read in on run time (now hard coded)
* clean the feeds and store in a file
* define database structure and load news into it
