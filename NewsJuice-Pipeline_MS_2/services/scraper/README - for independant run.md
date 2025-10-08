# Scraper

docker build -t newsjuice-scraper .
docker run --rm -v "${PWD}\..\artifacts:/data" newsjuice-scraper 

