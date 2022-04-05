from snipeit import SnipeIT
from jamf import API
import logging
from datetime import datetime, timedelta
import time
import requests
import re
import config
import os

STATUS_LABELS = {
    'Computing Lab': 11,
    'Departmental': 6,
    'Loaner': 13,
    'On Hold': 1,
    'Primary': 4,
    'Ready to Deploy': 2,
    'Received': 14,
    'Repurpose': 10,
    'Salvaged': 3,
    'Secondary': 7
}

snipeit = SnipeIT(config.SNIPEIT_API_URL, config.SNIPEIT_API_KEY)
jamf = API(hostname=config.JSS_API_URL, username=config.JSS_API_USERNAME, password=config.JSS_API_PASS, prompt=True)

now = datetime.now()
logging.basicConfig(filename=f'{config.LOGS_PATH}/{now.strftime("%d-%m-%Y_%H-%M-%S")}.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

def delete_old_logs():
    """Delete older logs. The time limit is specified in days in the configuration.
    """
    log_files = os.listdir(config.LOGS_PATH)
    cut_date = datetime.now() - timedelta(days=config.LOGS_DELETE_DAYS)

    for log_file in log_files:
        creation_date = datetime.strptime(time.ctime(os.path.getctime(config.LOGS_PATH + '/' + log_file)), '%a %b %d %H:%M:%S %Y')
        if creation_date < cut_date:
            os.remove(config.LOGS_PATH + '/' + log_file)

def get_updated_assets(start_date, offset=0):
    """Get a list off recently updated Apple assets

    Returns:
        list: list of assets
    """
    try:
        r = snipeit.assets.get(limit=config.SNIPEIT_PULL_SIZE, sort='updated_at', manufacturer_id=1, offset=offset)
        r = r['rows']
    except requests.exceptions.ConnectionError as err:
        logging.error(err)
    except requests.exceptions.Timeout as err:
        logging.error(err)
    except requests.exceptions.RequestException as err:
        logging.error(err)
    else:
        # If no other items
        if len(r) == 0:
            return None

        # If date of last pulled computer > start date
        if datetime.strptime(r[-1]['updated_at']['datetime'], '%Y-%m-%d %H:%M:%S') > start_date:
            new_items = get_updated_assets(start_date, offset + config.SNIPEIT_PULL_SIZE)
            if new_items is None:
                return r
            return r + new_items
        else:
            # Go backwords from last and remove items that are not in the timeframe
            for i in range(len(r) - 1, -1, -1):
                if datetime.strptime(r[i]['updated_at']['datetime'], '%Y-%m-%d %H:%M:%S') < start_date:
                    del r[i]
            return r

    return None

def get_jss_user(username: str):
    """Get user information from Jamf

    Args:
        username (str): username

    Returns:
        dict: user data
    """
    try:
        result = jamf.get('users/name/' + username)
    except Exception as err:
        logging.error(err)
        logging.debug(f'Error finding {username} in Jamf')
        return None

    user = result['user']
    formatted_result = {
        'username': user['name'],
        'realname': user['full_name'],
        'real_name': user['full_name'],
        'email_address': user['email_address'],
        'phone_number': user['phone_number'],
        'phone': user['phone_number'],
        'position': user['position']
    }

    return formatted_result

def format_asset_tag(name):
    """Get the asset tag out of computer name. Ex. HIDA-4121212 => 4121212

    Args:
        name (str): computer name

    Returns:
        str: asset tag
    """
    match = re.search(r'\d+', name)
    if match:
        return match.group()
    return None
    

def format_assets(asset_list):
    """Retrieve necessary information provided by SnipeIT API

    Args:
        asset_list (list): list of asset dictionaries from SnipeIT

    Returns:
        list: List of assets with formatted information ready for PUT in JAMF
    """
    formatted_assets = {}
    for asset in asset_list:
        logging.debug(f'{asset["name"]} {asset["serial"]}')
        asset_type = None
        if asset['category']['name'] == 'Tablet':
            asset_type = 'mobile_device'
        else:
            asset_type = 'computer'
        
        # General and Purchasing information
        asset_data = {
            asset_type: {
                'general': {
                    'name': asset['name'],
                    'asset_tag': asset['asset_tag'] if asset['asset_tag'] is not None else format_asset_tag(asset['name'])
                },
                'purchasing': {
                    'po_number': f"{asset['order_number']}".strip() if asset['order_number'] is not None else None,
                    'po_date': asset['purchase_date']['formatted'] if asset['purchase_date'] is not None else None,
                    'purchase_price': asset['purchase_cost'] if asset['purchase_cost'] is not None else None,
                    'warranty_expires': asset['warranty_expires']['formatted'] if asset['warranty_expires'] is not None else None,
                    'vendor': asset['supplier']['name'] if asset['supplier'] is not None else None
                }
            }
        }

        # User and Location information
        if asset['assigned_to'] is not None:
            if asset['assigned_to']['type'] == 'user':
                user = get_jss_user(asset['assigned_to']['username'])
                if user is not None:
                    asset_data[asset_type]['location'] = user
                    asset_data[asset_type]['location']['email_address'] = f"{asset['assigned_to']['username']}@asu.edu"
                else:
                    asset_data[asset_type]['location'] = {
                        'username': asset['assigned_to']['username'],
                        'realname': asset['assigned_to']['name'],
                        'real_name': asset['assigned_to']['name'],
                        'email_address': f"{asset['assigned_to']['username']}@asu.edu",
                        'position': None,
                        'phone': None,
                        'phone_number': None
                    }
            else: # If assigned to either location or asset
                asset_data[asset_type]['location'] = {
                    'username': 'hidait',
                    'realname': 'HIDA IT',
                    'real_name': 'HIDA IT',
                    'email_address': 'hidacs@asu.edu',
                    'position': None,
                    'phone': '480-965-6911',
                    'phone_number': '480-965-6911'
                }
        else: # If not assigned to anyone
            asset_data[asset_type]['location'] = {
                'username': None,
                'realname': None,
                'real_name': None,
                'email_address': None,
                'position': None,
                'phone': None,
                'phone_number': None
            }

        # Check if building and room custom fields exist
        if asset['custom_fields'] != []:
            asset_data[asset_type]['location']['building'] = asset['custom_fields']['Building']['value'] if asset['custom_fields']['Building'] is not None else None
            asset_data[asset_type]['location']['room'] = asset['custom_fields']['Room ']['value'] if asset['custom_fields']['Room '] is not None else None

        # Department
        if asset['company'] is not None:
            asset_data[asset_type]['location']['department'] = asset['company']['name']

        # Usage info
        if asset['status_label']['id'] in [STATUS_LABELS['Ready to Deploy'], STATUS_LABELS['Received']]:
            asset_data[asset_type]['extension_attributes'] = {
                'extension_attribute': [
                    {
                        'name': 'Usage',
                        'value': 'On Hold'
                    }
                ]
            }
        elif asset['status_label']['name'] in STATUS_LABELS:
            asset_data[asset_type]['extension_attributes'] = {
                'extension_attribute': [
                    {
                        'name': 'Usage',
                        'value': asset['status_label']['name']
                    }
                ]
            }
        else:
            logging.debug('Couldn\'t match usage information')

        formatted_assets[asset['serial']] = asset_data
    return formatted_assets

def update_jamf_computer(serial: str, data: dict):
    # Check if it is an iPad/mobile device or not
    if 'mobile_device' in data:
        try:
            jamf.put('mobiledevices/serialnumber/' + serial, data)
        except Exception as err:
            logging.error(err)
    else:
        try:
            jamf.put('computers/serialnumber/' + serial, data)
        except Exception as err:
            logging.error(err)

def main():
    logging.info('Deleting old logs...')
    delete_old_logs()

    start_date = datetime.now() - timedelta(hours=config.TIMEFRAME_HOURS)
    logging.info('Starting the script...')
    logging.info('Retrieving updated assets...')
    asset_list = get_updated_assets(start_date)
    logging.info('Formatting assets...')
    formatted_assets = format_assets(asset_list)
    logging.info('Uploading to JAMF...')
    for serial, data in formatted_assets.items():
        update_jamf_computer(serial, data)
    logging.info('DONE')

if __name__ == '__main__':
    main()
