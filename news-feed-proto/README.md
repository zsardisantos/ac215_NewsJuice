# news_feed_test

simple prototype for pulling newsfeeds from RSS source

do:

docker build -t news-feed -f Dockerfile .

docker run --rm -ti -v "$(pwd)":/app news-feed

and then in container: 

python news_feed_test.py

