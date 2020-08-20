import requests
from datetime import datetime
from utils import load_config
from typing import Dict
import logging
from requests.exceptions import HTTPError

class PassagePointRequests():

    def __init__(self, config_path: str = 'config.yml'):
        '''config_path should be a path to a config file in YAML format. Config should contain the username and password for the LibCal API, as well as the main API endpoint, all nested under a "PassagePoint" key. '''

        load_config(config_path=config_path, 
                    top_level_key='PassagePoint', 
                    config_keys=['username', 'password', 'pp_api_root',
                                 'login_endpt', 'create_visitor_endpt',
                                 'uniqueId_endpt', 'create_prereg_endpt',
                                 'get_destinations_endpt'],
                    obj=self)
        self.fetch_token()
        self.req_header = {'token': self.token, 'Content Type': 'application/json'}
        self.logger = logging.getLogger('pp_requests.py')


    def fetch_token(self):
        '''Retrieves a new authentication token, using supplied credentials.'''
        try:
            cred_body = {'username': self.username,
                         'password': self.password}
            resp = requests.post(self.pp_api_root + self.login_endpt, json=cred_body)
            resp.raise_for_status()
            token = resp.json()
            # TO DO: Check for expired token and create new if necessary
            # Check for errors in the JSON
            if 'error' in token:
                raise Exception(f'Error returned by PassagePoint authentication API: {token}')
            # Store the access token string
            self.token = token['token']
            return self
        except Exception as e:
            self.logger.error(f'Error fetching PassagePoint authentication token -- {e}')
            raise

    def _extract_id(self, api_data: Dict):
        '''Extracts the visitor ID(s) from the data returned from the createVisitor call.
        api_data should have a top-level key called "data."'''
        #TO DO: Handle situations where more than one data element is returned, if that ever happens.
        data = api_data['data']
        id_num = data[0]['id']
        return id_num

    def create_visitor(self, visitor: dict):
        '''Sends a POST request to create a new visitor using a uniqueId'''
        params = {'category': 'Visitor',
                  'firstName': visitor['firstName'],
                  'lastName': visitor['lastName'],
                  'uniqueId': visitor['barcode']}
        try:
            resp = requests.post(self.pp_api_root + self.create_visitor_endpt,
                                 headers=self.req_header,
                                 params=params)
            resp.raise_for_status()
            visitor_data = resp.json()
            if 'error' in visitor_data:
                raise Exception(visitor_data)
            return self._extract_id(visitor_data)
        except HTTPError:
            if 'ALREADY_EXIST_UNIQUE_ID' in resp.text:
                # If the request fails because the visitor has already been created, try to get the Visitor ID
                self.logger.debug(f'Visitor {visitor['barcode']} already exists in PassagePoint; getting Visitor ID.')
                return self.get_visitor_bybarcode(visitor['barcode'])
            else:
                self.logger.error(f'Error in calling createVisitor API: {resp.reason}')
                self.logger.error(f'Error response: {resp.text}')
                raise
        except Exception as e:
            self.logger.error(f'Error creating visitor in PassagePoint for barcode {barcode} -- {e}')
            raise


    def get_visitor_bybarcode(self, barcode: str):
        '''Retrieves the visitor ID from PassagePoint for a provided barcode in the visitor's unique ID field.'''
        try:
            params = {'uniqueId': barcode}
            resp = requests.get(self.pp_api_root + self.uniqueId_endpt,
                                headers=self.req_header,
                                params=params)
            resp.raise_for_status()
            visitor_data = resp.json()
            return self._extract_id(visitor_data)
        except Exception as e:
            print(f'Error getting visitor from PassagePoint with barcode {barcode} -- {e}')
            raise


    def create_prereg(self, booking: dict, visitor: str):
        '''Creates a Pre-Registration with the visitor ID and LibCal data.
        Requires a booking dict with a visitorId, startTime and endTime
        '''
        try:
            format_str = '%Y-%m-%dT%H:%M:%S%z'
            booking["startTime"] = str(int(datetime.strptime(booking['startTime'], format_str).timestamp()))
            booking["endTime"] = str(int(datetime.strptime(booking['endTime'], format_str).timestamp()))
            booking["visitorId"] = visitor
            booking["destination"] = "LibCal"  # needs to exist in PP
            resp = requests.post(self.pp_api_root + self.create_prereg_endpt,
                                 headers=self.req_header,
                                 json=booking)
            resp.raise_for_status()
            prereg_data = resp.json()
            if 'error' in prereg_data:
                raise Exception(prereg_data)
            return self._extract_id(prereg_data)
        except HTTPError:
            self.logger.error(f'Error in calling createPreReg API: {resp.reason}')  
            self.logger.error(f'Response body: {resp.text}')
            raise     
        except Exception as e:
            print(f'Error creating pre-registration for booking {booking} -- {e}')
            raise


    def get_destinations(self):
        '''Retrieves the destinations from PassagePoint and returns as dict'''
        try:
            resp = requests.get(self.pp_api_root + self.get_destinations_endpt,
                                headers=self.req_header)
            resp.raise_for_status()
            destinations = resp.json()
            return destinations
        except Exception as e:
            print(f'Error getting PassagePoint destinations -- {e}')
            raise


if __name__ == '__main__':
    passagept = PassagePointRequests()
    print(passagept.token)
    print(passagept.req_header)
 #   visitor_data = passagept.create_visitor({'firstName': 'Test',
 #                                            'lastName': 'Patron',
 #                                            'barcode': '012301230123012301'})
 #   print(visitor_data)
    prereg = passagept.create_prereg({"startTime": "2020-08-22T20:05:00-04:00", "endTime": "2020-08-22T22:05:00-04:00"}, '137505764541138')
    print(prereg)
