import requests
from utils import load_config
from typing import Dict, List
from requests.exceptions import HTTPError
import logging


class LibCalRequests():

    def __init__(self, config_path: str = 'config.yml'):
        '''config_path should be a path to a config file in YAML format. Config should contain the client id and client secret for the LibCal API, as well as the authentication and bookings endpoints, all nested under a "LibCal" key. '''

        self.logger = logging.getLogger('libcal_requests.py')
        load_config(config_path=config_path, 
                    top_level_key='LibCal', 
                    config_keys=['client_id', 'client_secret', 'credentials_endpt', 'bookings_endpt', 'locations', 'primary_id_field'],
                    obj=self)
        self.fetch_token()


    def retrieve_bookings_by_location(self):
        '''Loops through locations provided in the config file to retrieve the bookings associated with each.'''
        bookings = []
        for location in self.locations:
            try:
                booking = self.get_bookings(location)
                bookings.extend(booking)
            except Exception as e:
                self.logger.error(f'Failed to get bookings for {location["name"]} -- {e}')
        return bookings


    def check_status(self, booking: Dict):
        '''To filter out bookings with particular kinds of statuses.'''
        if 'Cancelled' in booking:
            return False
        return True

    def dedup_bookings(self, bookings: List):
        '''Identified duplicate bookIds, which can occur when appointments are made using the LibCal admin module for the same user for the same time for different seats.
        For the purposes of this integration, we count those as a single booking.'''
        uniq_bookings = {b['bookId'] for b in bookings}
        # Check for non-unique bookId's in the list
        if len(uniq_bookings) < len(bookings):
            deduped = []
            for booking in bookings:
                if booking['bookId'] in uniq_bookings: # If this is in the unique set, store it
                    deduped.append(booking)
                    uniq_bookings.remove(booking['bookId']) # Remove this Id from the set 
            return deduped
        return bookings

    def get_bookings(self, location: Dict, retry: bool = False):
        '''Fetches the space appointments for today\'s date (default).
        location argument should be a dictionary with keys "name" and "id" from the config file.
        retry is a flag to manage the need to retry the request after refreshing the token. If retry is true, the call will not be retried again.'''
        try:
            headers, params = self.prepare_bookings_req(location)
            resp = requests.get(self.bookings_endpt, 
                                headers=headers,
                                params=params)
            resp.raise_for_status()
            data = resp.json()
            # Check for error in the JSON
            if 'error' in data:
                raise Exception(f'Error returned by LibCal bookings API: {bookings}')
            bookings = []
            # Filter out cancelled bookings
            # Rename the primary ID field, which has a non-descriptive identifier in the LibCap API
            for booking in data:
                if not self.check_status(booking['status']):
                    continue
                booking['primary_id'] = booking.get(self.primary_id_field)
                bookings.append(booking)
            bookings = self.dedup_bookings(bookings)
            return bookings
        except HTTPError:
            # Test for expired token
            if (resp.reason == 'Unauthorized') and not retry:
                self.logger.debug('LibCal token expired. Fetching new token.')
                self.fetch_token()
                return self.get_bookings(location, retry=True)
            self.logger.error(f'Error calling space/bookings API - {resp.reason}')
            self.logger.error(f'Error response: {resp.text}')
            raise
        except Exception as e:
            self.logger.error(f'Error fetching bookings data. -- {e}')
            raise


    def prepare_bookings_req(self, location: Dict):
        '''Creates the authentication header and the default parameters for the LibCal bookings calls.
        location argument should be a dictionary with keys "name" and "id." The id field is used to pass the location to the bookings query.'''
        header = {'Authorization': f'Bearer {self.token}'}
        params = {'limit': 100,             # Max value
                'lid': location['id'],
                'formAnswers': 1} # Includes additional form fields 
        return header, params


    def fetch_token(self):
        '''Retrieves a new authentication token, using supplied credentials.'''
        try:
            cred_body = {'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'client_credentials'}
            resp = requests.post(self.credentials_endpt, json=cred_body)
            resp.raise_for_status()
            token = resp.json()
            # TO DO: Check for expired token and create new if necessary
            # Check for errors in the JSON
            if 'error' in token:
                raise Exception(f'Error returned by LibCal authentication API: {token}')
            # Store the access token string
            self.token = token['access_token']
            return self
        except HTTPError:
            self.logger.error(f'Error on LibCal authentication API: {resp.reason}')
            self.logger.error(f'Error body: {resp.text}')
            raise
        except Exception as e:
            self.logger.error('Error fetching LibCal authentication token.')
            raise


if __name__ == '__main__':
    libcal = LibCalRequests('config.yml')
    bookings = libcal.retrieve_bookings_by_location()
    print(bookings)
