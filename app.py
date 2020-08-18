from libcal_requests import LibCalRequests
from alma_requests import AlmaRequests
from sqlite_cache import SQLiteCache
<<<<<<< HEAD
from pp_requests import PassagePointRequests
=======
>>>>>>> b3de1eaf35decb3feb7cdf2c5ec318459d50cb87
import logging
import argparse
from typing import Dict, List

# Configure logging 
#logging.basicConfig(filename='./libcal2pp.log')

LOG = logging.getLogger('libcal2pp')
# For output to terminal
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
handler.setFormatter(formatter)
LOG.addHandler(handler)

class LibCal2PP():

    def __init__(self, config_path: str = './config.yml', interval=None):
        '''
        config_path, if provided, should point to a YAML file with config information for the LibCal, PassagePoint, and Alma API's. 
        interval should be the time (in seconds) to pause between runs of the app. If not provided, the app runs once and quits.
        '''
        # Initialize components
        LOG.debug('Initializing components')
        try:
            self.libcal = LibCalRequests(config_path)
            self.alma = AlmaRequests(config_path)
            self.cache = SQLiteCache()
            self.pp = PassagePointRequests(config_path)
        except Exception as e:
            LOG.error(f'Error on init -- {e}')


    def log_new_bookings(self):
        '''Retrieve bookings from LibCal and create new pre-registrations in PassagePoint.'''
        LOG.debug('Querying LibCal API')
        try:
            bookings = self.libcal.retrieve_bookings_by_location()
        except Exception as e:
            LOG.error(f'Error retrieving new bookings -- {e}')
            return
        LOG.debug(f'Bookings retrieved: {bookings}')
        # Filter out appointments already in the database
        new_bookings = [booking for booking in bookings if not self.cache.appt_lookup(booking['bookId'])]
        LOG.debug(f'New bookings: {new_bookings}')
        # Get the user info we need for PassagePoint, registering any new users in the process
        users = self.process_users(new_bookings)
        # If no valid users, exit
        if not users:
            return
        # Add the VistorId for the Passage Point user to each appointment
        LOG.debug(f'Creating new pre-registrations in Passage Point.')
        registrations = []
        for booking in new_bookings:
            primary_id = booking['primary_id']
            visitor_id = users.get(primary_id)
            # User not registered -- skip
            if not visitor_id:
                continue
            pre_reg = {'startTime': booking['fromDate'],
                        'endTime': booking['toDate']}
            try:
                # Make call to Passage Point and get appointment Id
                prereg_id = self.pp.create_prereg(pre_reg, visitor_id)
                # Save the prereg Id for insertion into the cache
                registrations.append({'prereg_id': prereg_id,
                                    'appt_id': booking['bookId']})
            except Exception as e:
                LOG.error(f'Error creating pre_reg for appointment {booking} -- {e}')
                continue
        if registrations:
            LOG.debug('Saving new pre-registrations to cache.')
            try:
                self.cache.add_appt(registrations)
            except Exception as e:
                LOG.error(f'Error saving pre-registrations -- {e}')

    def process_users(self, bookings: List[Dict[str, str]]):
        '''Given new appointments from LibCal, check for their presence in the cache and if necessary, retrieve their barcodes from Alma and register them in PassagePoint.'''
        LOG.debug(f'Checking for users in the cache.')
        # Users will be a lookup by primary ID to visitor ID
        users = {}
        # New users will be a lookup by primary ID to other user info
        new_users = {}
        for b in bookings:
            primary_id = b['primary_id']
            # Avoid querying for the same user more than once per batch of appointments
            if (primary_id not in users) and (primary_id not in new_users):
                try:
                    user = self.cache.user_lookup(primary_id)
                except Exception as e:
                    LOG.error(f'Error processing user {primary_id} -- {e}')
                    continue
            # If the user isn't in the cache, need to get their info from Alma
                if not user:
                    new_users[primary_id] = {'firstName': b['firstName'],
                                             'lastName': b['lastName']}
            # Otherwise, record their PassagePoint Id
                else:
                    users[primary_id] = user['visitor_id']  

        if new_users:
            # Register the new users and get back their PassagePoint ID's
            registered_users = {user['primary_id']: user for user in self.register_new_users(new_users) if user}
            try:
                LOG.debug(f'Adding newly registered users to the cache: {registered_users}.')
                self.cache.add_users(registered_users.values())
            except Exception as e:
                LOG.error(f'Error saving new users -- {e}')
            # Update the list of users for registering appointments in Passage Point
            users.update({k: v['visitor_id'] for k, v in registered_users.items()})
        return users

    def register_new_users(self, new_users: Dict[str, Dict[str, str]]):
        '''new_users should be a dictionary whose keys are Alma Primary IDs and whose values are dictionaries containing additional information from LibCal required to register new users in PassagePoint.'''
        LOG.debug(f'Getting new user info from Alma for {new_users}.')
        # AlmaRequest.main returns a dict mapping primary ID's to barcodes
        try:
            pid_to_barcode = self.alma.main(new_users.keys())
        except Exception as e:
            LOG.error(f'Error fetching user data for new users -- {e}')
            return None
        # Register new PassagePoint users -- function should return for each user, their Visitor Id
        for pid, barcode in pid_to_barcode.items():
            # Update the user info with the barcode from Alma
            new_user = new_users[pid]
            new_user['barcode'] = barcode
            try:
                LOG.debug(f'Creating Passage Point user record: {new_user}.')
                # Call to Passage Point API here
                visitor_id = self.pp.create_visitor(new_user)
                # Return the user info from Alma and PP
                yield {'visitor_id': visitor_id,
                        'primary_id': pid,
                        'barcode': barcode}
            except Exception as e:
                LOG.error(f'Error creating user for user {pid} -- {e}')
                continue
                
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # Accepts an option --debug flag to set the log level to DEBUG (most verbose)
    parser.add_argument('--debug', action="store_const", const=logging.DEBUG, default=logging.WARNING)
    args = parser.parse_args()
    LOG.setLevel(args.debug)
    app = LibCal2PP()
    app.log_new_bookings()



