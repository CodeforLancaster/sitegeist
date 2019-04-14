# SiteGeist

### Sentiment analysis of geofenced tweets

To setup, please run `./setup.sh`.

Secondly, run `main.py` with the following arguments:

```
-g --geofence The geofence from which to pull tweets
-t --twitter-api-keys The twitter api keys with which to pull tweets

```

For example:

```
python3 main.py -g lat1 lon1 lat2 lon2 -t <consumer key> <consumer secret> <access token key> <access token secret>
```