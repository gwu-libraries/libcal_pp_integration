import requests
from utils import load_config
from typing import Dict

class LibCalRequests():

    def __init__(self, config_path: str):
        '''config_path should be a path to a config file in YAML format. Config should contain the client id and client secret for the LibCal API, as well as the authentication and bookings endpoints, all nested under a "LibCal" key. '''

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
                # TO DO: Log exceptions
                print(f'Failed to get bookings for {location["name"]}')
                print(e)
        return bookings

    def get_bookings(self, location: Dict):
        '''Fetches the space appointments for today\'s date (default).
        location argument should be a dictionary with keys "name" and "id" from the config file.'''
        try:
            headers, params = self.prepare_bookings_req(location)
            resp = requests.get(self.bookings_endpt, 
                                headers=headers,
                                params=params)
            resp.raise_for_status()
            bookings = resp.json()
            # Check for error in the JSON
            if 'error' in bookings:
                raise Exception(f'Error returned by LibCal bookings API: {bookings}')
            return bookings
        except Exception as e:
            print('Error fetching bookings data.')
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
        except Exception as e:
            print('Error fetching LibCal authentication token.')
            raise
            
if __name__ == '__main__':
    libcal = LibCalRequests('config.yml')
    bookings = libcal.retrieve_bookings_by_location()
    print(bookings)
