# Telegram-SpottedDMI-Bot
[![Test and docs](https://github.com/UNICT-DMI/Telegram-SpottedDMI-Bot/actions/workflows/prod.workflow.yml/badge.svg)](https://github.com/UNICT-DMI/Telegram-SpottedDMI-Bot/actions/workflows/prod.workflow.yml)
[![Docker image](https://github.com/UNICT-DMI/Telegram-SpottedDMI-Bot/actions/workflows/docker.yml/badge.svg)](https://github.com/UNICT-DMI/Telegram-SpottedDMI-Bot/actions/workflows/docker.yml)
[![CodeFactor](https://www.codefactor.io/repository/github/unict-dmi/telegram-spotteddmi-bot/badge)](https://www.codefactor.io/repository/github/unict-dmi/telegram-spotteddmi-bot)

**Telegram-SpottedDMI-Bot** is the platform that powers **[@Spotted_DMI_Bot](https://telegram.me/Spotted_DMI_Bot)**, a Telegram bot that let students send an anonymous message to the channel community.

### Using the live version
The bot is live on Telegram with the username [**@Spotted_DMI_Bot**](https://telegram.me/Spotted_DMI_Bot).
To see the posts, once published, check [**Spotted DMI**](https://t.me/Spotted_DMI)
Send **'/start'** to start it, **'/help'** to see a list of commands.

Please note that the commands and their answers are in Italian.

## Table of contents

- **[:wrench: Setting up a local istance](#wrench-setting-up-a-local-istance)**
- **[:whale: Setting up a Docker container](#whale-setting-up-a-docker-container)**
- **[:bar_chart: _\[Optional\]_ Setting up testing](#bar_chart-optional-setting-up-testing)**
- **[:books: Documentation](#books-documentation)**

---

## :wrench: Setting up a local istance

#### System requirements
- [Python 3 (3.8.5)](https://www.python.org/downloads/)
- python-pip3

#### Install with *pip3*
Listed in requirements.txt.  
The main ones are:
- [python-telegram-bot](https://pypi.org/project/python-telegram-bot/)
- [requests](https://pypi.org/project/requests/)
- [PyYAML](https://pypi.org/project/PyYAML/)

### Steps:
- Clone this repository
- \[_OPTIONAL_\] Create _"data/yaml/reactions.yaml"_ and edit the desired parameters.
- Create _"config/settings.yaml"_ and edit the desired parameters. **Make sure to add a valid _token_ setting**.
- Make sure the bot is in present both in the admin group and in the spot channel. It may need to have admin privileges. If comments are enabled, the bot has to be in the comment group too as an admin.
- What follows are some example settings with explaination for each:
  ```yaml
  debug:
    local_log: false        # save each and every message in a log file. Make sure the path "logs/messages.log" is valid when enabled

  meme:
    channel_group_id: -100  # id of the group associated with the channel. Required if comments are enabled
    channel_id: -200        # id of the channel to which the bot will send the approved memes
    channel_tag: '@channel' # tag of the channel to which the bot will send the approved memes
    comments: true          # whether or not the channel the bot will send the memes to has comments enabled
    group_id: -300          # id of the admin group the memebot will use
    n_votes: 2              # votes needed to approve/reject a pending post
    remove_after_h: 12      # number of hours after wich pending posts will be automatically by /clean_pending
    reset_on_load: false    # whether or not the database should reset every time the bot launches. USE CAREFULLY
    report_wait_mins: 30    # number of minutes the user has to wait before being able to report another user again
    tag: false              # whether or not the bot should tag the admins or just write their usernames
     # whether the bot should replace any anonymous comment with a message by itself. 
     # The bots must have delete permission in the group and comments must be enabled
    replace_anonymous_comments: true

  test:
    api_hash: XXXXXXXXXXX   # hash of the telegram app used for testing
    api_id: 123456          # id of the telegram app used for testing
    remote: false           # whether you want to test the remote database, the local one or both
    session: XXXXXXXXXXXX   # session of the telegram app used for testing
    bot_tag: '@test_bot'    # tag of the telegram bot used for testing. Include the '@' character
    token: xxxxxxxxxxxx     # token for the telegram bot used for testing
    #... all the tags above. They will be overwritten when testing

  token: xxxxxxxxxxxx       # token of the telegram bot
  bot_tag: '@bot'           # tag of the telegram bot
  ```
- **Run** `python3 main.py`

## :whale: Setting up a Docker container

#### System requirements
- Docker


### Steps:
- Clone this repository
- \[_OPTIONAL_\] Create _"data/yaml/reactions.yaml"_ and edit the desired parameters.
- Create _"config/settings.yaml"_ and edit the desired parameters. **Make sure to add a valid _token_ setting**.
- \[_OPTIONAL_\] You could also leave the settings files alone, and use the environment variables on the container instead.
- Make sure the bot is in present both in the admin group and in the spot channel. It may need to have admin privileges. If comments are enabled, the bot has to be in the comment group too as an admin.
- All the env vars with the same name (case insensitive) will override the ones in the settings file.
To update the **meme** settings, prefix the env var name with **MEME_**. The same is true for the **test** settings, that have to be prefixed with **TEST_**.
- **Run** `docker build --tag botimage .` 
- **Run** `docker run -d --name botcontainer -e TOKEN=<token_arg> [other env vars] botimage`

### To stop/remove the container:
- **Run** `docker stop botcontainer` to stop the container
- **Run** `docker rm -f botcontainer` to remove the container

## :bar_chart: _[Optional]_ Setting up testing

#### Install with *pip3*
Listed in requirements_dev.txt
- [pytest](https://pypi.org/project/pytest/)

#### Steps:
- **Run** `pytest`

## :books: Documentation
Check the gh-pages branch

[Link to the documentation](https://unict-dmi.github.io/Telegram-SpottedDMI-Bot/)
