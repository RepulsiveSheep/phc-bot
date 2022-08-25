# u/phc-bot

Source code for the&mdash; *ahem* bot. You know the one.

The core of the bot is in the [app.py][1] file. main.py is just a Flask endpoint for Heroku, which is where the bot
is currently hosted.

## Summoning

Just summon the bot by its name (u/phc-bot) on whichever subreddit you please. You don't have to summon it on
the PHC subreddit &ndash; it's always checking the posts there &ndash; but feel free to do so anyway.

## Setup

### Requirements

Other than the usual package requirements (`pip install -r requirements.txt`), you need to install tesseract-ocr.
On Ubuntu or other Debian-based distros, you can install it with `sudo apt install tesseract-ocr tesseract-ocr-eng`.

I can't remember, but I think you'd also need to install Python source files (`sudo apt install python3-dev`),
so if you see `#include <Python.h>` in an error log somewhere, try that.

### Environment variables
First you need to set up environment variables. You can use the `.env` file for this. See [`.env.sample`][2]
for all possible environment variables. The ones that start with `REDDIT_` are mandatory.

See the guide on obtaining client secret and client ID [here][3].

If you want to use a custom database other than Sqlite (e.g. Postgres on Heroku), set `DATABASE_URL` as well.

### Database

Just run the following command, and you should be good to go.

```bash
./create_schema.py
```

## Running the bot

**Note**: Please don't run the bot yourself, unless u/phc-bot is dead for good. There isn't much point in
two instances of the bot running at the same time.

The bot operates in two different modes: `submissions` and `mentions`. Each mode can be invoked as `./app.py {mode}`.

In `submissions` mode, it processes all the posts from the designated subreddit.
In `mentions` mode, it processes each "mention", or call to summon (i.e. /u/phcbot) made by users.

main.py, which is what runs on Heroku, runs in the two modes concurrently using threads.

### Docker

You can also run this image with docker. The included [Dockerfile][5] is meant for production (runs Flask server via 
gunicorn), but you can easily mount the source directory as a volume and use it for development as well.

Start by building the image:

```bash
docker build --tag phc-bot .
```

Before you can start using the container, you need to create the schema in whatever database you're using (either
SQLite or an external one, configure this using `.env` file).

```
docker run --name phc-bot --env-file .env -p 8000:8000 -d phc-bot
docker exec phc-bot python create_schema.py
```

For development:

```bash
docker run --name phc-bot -d -v "$(pwd):/app" --env-file .env -p 8000:8000 phc-bot --reload
docker exec phc-bot python create_schema.py
```

This will run mount the current folder to the container's /app folder, and run gunicorn with the `--reload` flag,
so any time you make changes to your host directory, gunicorn will reload itself.

## Contributing

This is a pretty dumb bot at this point, so feel free to improve it!

[1]: app.py
[2]: .env.sample
[3]: https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example
[4]: https://heroku.com/deploy
[5]: Dockerfile
