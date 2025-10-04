# News Feed Test

A simple prototype for pulling news feeds from an RSS source.

---

## Getting Started

### 1. Build the Docker image

```bash
docker build -t news-feed -f Dockerfile .
```

### 2. Run the Docker container

```bash
docker run --rm -ti -v "$(pwd)":/app news-feed
```

### 3. Execute the test script inside the container

```bash
python news_feed_test.py
```

---

## Possible Next Steps

- Identify Harvard-specific sources.  
- Support additional formats beyond RSS.  
- Move source URLs into a configuration file that can be read at runtime (currently hard-coded).  
- Clean and preprocess the feeds, then store them in a structured file.  
- Define a database schema and load the cleaned news data into it.  

---

## Notes

- This is an early-stage prototype.  
- For now, only a single RSS feed is hard-coded.  
- Designed to be a lightweight experiment to inform the next iteration of the project.