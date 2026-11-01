# Street Source social

Images and the card renderer for Street Source's social posts.

- `renderer/make_week.py` renders branded 1080x1440 cards from a JSON spec.
- `images/<week-start>/` holds each week's cards and the spec they were made from.

Images are public so the posting automation can fetch them by URL.

The Action runs every 30 minutes, and on any change to renderer/.
