import argparse
import logging
import sched, time
from logging.handlers import SMTPHandler
from typing import Dict, List
from libcal_requests import LibCalRequests
from alma_requests import AlmaRequests
from sqlite_cache import SQLiteCache
from pp_requests import PassagePointRequests
from utils import load_config, check_config

# Configure logging 

def create_loggers(config: Dict):
    '''config should contain a key called Emails'''
    email_config = check_config(config=config, 
                           top_level_key='Emails', 
                           config_keys=['from_email', 'from_username', 'from_password', 'smtp_host', 'to_email'])
    # For ERROR output to email
    smtphandler = SMTPHandler(mailhost=(email_config["smtp_host"], 587), fromaddr=email_config["from_email"],
                          toaddrs=email_config["to_email"], subject="LibCal-PP App ERROR",
                          credentials=(email_config["from_username"], email_config["from_password"]), secure=())
    smtphandler.setLevel("ERROR")
    # For output to terminal
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s:%(message)s')
    handler.setFormatter(formatter)
    smtphandler.setFormatter(formatter)
    logger = logging.getLogger('lcpp')
    logger.addHandler(smtphandler)
    logger.addHandler(handler)
    return logger

class LibCal2PP():

    def __init__(self, config_path: str = './config.yml', interval=None):
        '''
        config_path, if provided, should point to a YAML file with config information for the LibCal, PassagePoint, and Alma API's. 
        interval should be the time (in seconds) to pause between runs of the app. If not provided, the app runs once and quits.
        '''
        # Load the config file
        self.config = load_config(config_path)
        # Initialize components
        self.logger = create_loggers(self.config)
        self.logger.debug('Initializing components')
        # Do not catch errors here - if any of these fail, we want the program to exit
        self.libcal = LibCalRequests(self.config)
        self.alma = AlmaRequests(self.config)
        self.cache = SQLiteCache()
        self.pp = PassagePointRequests(self.config)
        # Should contain the value for the interval for scheduled execution
        self.interval = self.config['LCPP']['interval']

    def log_new_bookings(self):
        '''Retrieve bookings from LibCal and create new pre-registrations in PassagePoint.'''
        self.logger.debug('Querying LibCal API')
        try:
            bookings = self.libcal.retrieve_bookings_by_location()
        except Exception as e:
            self.logger.error(f'Error retrieving new bookings -- {e}')
            return
        self.logger.debug(f'Bookings retrieved: {len(bookings)}')
        # Filter out appointments already in the database 
        new_bookings = [booking for booking in bookings if not self.cache.appt_lookup(booking['bookId'])]
        if not new_bookings:
            self.logger.debug('No new bookings.')
            return
        self.logger.debug(f'New bookings: {new_bookings}')
        # Get the user info we need for PassagePoint, registering any new users in the process
        users = self.process_users(new_bookings)
        # If no valid users, exit
        if not users:
            return
        # Add the VistorId for the Passage Point user to each appointment
        registrations = []
        for booking in new_bookings:
            primary_id = booking['primary_id']
            visitor_id = users.get(primary_id)
            # User not registered -- skip
            if not visitor_id:
                continue
            # Create the prereg data, using the LibCal timestamps and location ID
            pre_reg = {'startTime': booking['fromDate'],
                        'endTime': booking['toDate'],
                        'destination': booking['lid']}
            try:
                self.logger.debug(f'Creating new pre-registration in Passage Point for visitor {visitor_id}.')
                # Make call to Passage Point and get appointment Id
                prereg_id = self.pp.create_prereg(pre_reg, visitor_id)
                # Save the prereg Id for insertion into the cache
                registrations.append({'prereg_id': prereg_id,
                                    'appt_id': booking['bookId']})
            except Exception as e:
                continue
        if registrations:
            self.logger.debug('Saving new pre-registrations to cache.')
            try:
                self.cache.add_appt(registrations)
            except Exception as e:
                self.logger.exception(f'Error saving pre-registrations -- {e}')


    def process_users(self, bookings: List[Dict[str, str]]):
        '''Given new appointments from LibCal, check for their presence in the cache and if necessary, retrieve their barcodes from Alma and register them in PassagePoint.'''
        self.logger.debug(f'Checking for users in the cache.')
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
                    self.logger.error(f'Error processing user {primary_id} -- {e}')
                    continue
            # If the user isn't in the cache, or if the records lacks a visitor_id, need to get their info from Alma
                if not user or not user.get('visitor_id'):
                    new_users[primary_id] = {'firstName': b['firstName'],
                                             'lastName': b['lastName'],
                                             'email': b['email'],
                                             'primary_id': primary_id}
            # Otherwise, record their PassagePoint Id
                else:
                    users[primary_id] = user['visitor_id']  

        if new_users:
            # Register the new users and get back their PassagePoint ID's
            registered_users = {user['primary_id']: user for user in self.register_new_users(new_users) if user}
            try:
                self.logger.debug(f'Adding newly registered users to the cache.')
                self.cache.add_users(registered_users.values())
            except Exception as e:
                self.logger.exception(f'Error saving new users -- {e}')
            # Update the list of users for registering appointments in Passage Point
            users.update({k: v['visitor_id'] for k, v in registered_users.items()})
        return users


    def register_new_users(self, new_users: Dict[str, Dict[str, str]]):
        '''new_users should be a dictionary whose keys are Alma Primary IDs and whose values are dictionaries containing additional information from LibCal required to register new users in PassagePoint.'''
        self.logger.debug(f'Getting new user info from Alma for {list(new_users.keys())}.')
        # AlmaRequest.main returns a dict mapping primary ID's to barcodes
        try:
            pid_to_users = self.alma.main(new_users.keys())
        except Exception as e:
            self.logger.exception(f'Error fetching user data for new users -- {e}')
            return None
        # Register new PassagePoint users -- function should return for each user, their Visitor Id
        for pid, user in pid_to_users.items():
            # Update the user info with the barcode and user_group from Alma
            new_user = new_users[pid]
            new_user.update(user) 
            try:
                self.logger.debug(f'Creating PassagePoint visitor record: {pid}.')
                # Call to Passage Point API here
                visitor_id = self.pp.create_visitor(new_user)
                # Return the user info from Alma and PP
                yield {'visitor_id': visitor_id,
                        'primary_id': pid,
                        'barcode': user['barcode']}
            except Exception as e:
                self.logger.exception(f'Error creating PassagePoint visitor record for user {pid} -- {e}')
                continue

def run_app(app, scheduler):
    '''Function to schedule the app. 
    app should be an instance of LibCal2PP. This function calls the log_new_bookings method.
    scheduler should be an instance of sched.scheduler.'''
    app.log_new_bookings()
    # Schedule the next run of this function
    scheduler.enter(app.interval, 1, run_app, argument=(app, scheduler))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # Accepts an option --debug flag to set the log level to DEBUG (most verbose)
    parser.add_argument('--debug', action="store_const", const=logging.DEBUG, default=logging.WARNING)
    args = parser.parse_args()
    app = LibCal2PP()
    app.logger.setLevel(args.debug)
    # Initialize sched object
    scheduler = sched.scheduler(time.time, time.sleep)
    run_app(app, scheduler)
    # Run the scheduling thread
    scheduler.run()

