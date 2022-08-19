## How does it work?

Currently, script is hosted on DS08 MacMini under Anthony’s account.

### Crontab

Crontab is used to schedule the script to run every 12 hours, at 11:59 and 23:59. To edit crontab, use “crontab -e”, the configuration file will open with a *vi(m)* editor. This configuration will be erased when computer restarts. DS08 computer right now is on 24/7

```bash
59 11 * * * ~/.scripts/snipeit2jamf.sh
59 23 * * * ~/.scripts/snipeit2jamf.sh
```

### Shell Script

The shell script that is used to run the primary script is located in “/Users/anthony/.scripts” directory in [snipeit2jamf.sh](http://snipeit2jamf.sh) file.

```bash
source /Users/anthony/Documents/WickedScript/venv/bin/activate && 
python /Users/anthony/Documents/WickedScript/main.py && 
deactivate
```

This script activates a virtual Python environment, runs the python script, and deactivates the environment.

### Python Script

The python script is stored in “/Users/anthony/Documents/WickedScript” directory. It is pulled from [https://github.com/hidadev/WickedScript](https://github.com/hidadev/WickedScript) repository.

## Script Configuration

Configuration variables are stored in the “config.py” file. 

```python
SNIPEIT_API_KEY = '75ud-StG2RJ6uwWLQ626tHneSY2Ulc4...'
SNIPEIT_API_URL = 'https://hida-snipeit.hida.asu.edu'
JSS_API_USERNAME = 'apieditor'
JSS_API_PASS = 'password'
JSS_API_URL = 'https://jss.hida.asu.edu:8443'
SNIPEIT_PULL_SIZE = 25  # This is the amount of updated computers 
                        # pulled at one time. Most of the time, there are
                        # only a few computers updated in one day, meaning
                        # there is no need to pull all of them
TIMEFRAME_DAYS = 0 # Amount of days to look back for updated assets
TIMEFRAME_HOURS = 12.5 # This is the amount of hours to look back for updated
                       # computers, since script runs every 12hrs, we do 12 + 30 min buffer
PATH = '/Users/anthony/Documents/WickedScript' # Path to script main folder location
LOGS_DELETE_DAYS = 7 # Amount of days after which logs get deleted
```

## Logs

Logs are stored in the “logs” folder and date named. The logs should provide enough information to know whether there was something wrong or not. Some errors are to be expected, such as when trying to update a freshly pre-stage enrolled computer that hasn’t been turned on yet, so it doesn’t appear in Jamf.

## Failed Assets

If an asset can’t be updated, as it is the case with pre-staged computers that don’t appear in Jamf yet, they will be added to the “failed_assets.json” file and will attempt to update the next time script runs. 

## Manually Run the Script

To manually run the script, you will need to navigate to the Python script directory on a host machine, activate python virtual environment “source /venv/bin/activate” and simply running the [main.py](http://main.py) file “python3 main.py”

## Force Update All

Let’s say something went wrong, and you need to make sure that all assets are updated. You can simply change script configuration for TIMEFRAME_DAYS to 9999run the script and include all of the assets by

## Starting Over

“I have messed up and ruined the thing, how do I start over?” or if you need to start the script on a new machine.

1. Make sure Python3 is installed on your host machine and it is in path
2. Clone the code from [https://github.com/hidadev/WickedScript](https://github.com/hidadev/WickedScript) 
3. Create a virtual python environment by using “python3 -m venv venv”
4. Use pip to install required dependancies, “pip install -r requirements.txt”
5. Duplicate “sample_config.py” to “config.py” and fill out configuration settings, reference “Script Configuration” part of this guide.
6. Create a shell script in a directory of your choice, reference the Shell Script part of this guide.
7. Create a crontab entry to run the script, reference Crontab part of this guide.

## Potential Improvements

- Store last successful update date so if something goes wrong on the next one, there is a reference point for assets that were not able to update
- Create command line arguments to run script instead of modifying configuration
- Find a better way to schedule
