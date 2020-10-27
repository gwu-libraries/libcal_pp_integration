import requests
from datetime import datetime
from utils import check_config, load_config
from typing import Dict
import logging
from requests.exceptions import HTTPError


class PassagePointRequests():

    def __init__(self, config: Dict):
        '''config should contain the username and password for the LibCal API, as well as the main API endpoint, all nested under a "PassagePoint" key. '''

        self.logger = logging.getLogger('lcpp.pp_requests')
        check_config(config=config, 
                    top_level_key='PassagePoint', 
                    config_keys=['username', 'password', 'pp_api_root',
                                 'login_endpt', 'create_visitor_endpt',
                                 'uniqueId_endpt', 'create_prereg_endpt',
                                 'get_destinations_endpt', 'user_mapping',
                                 'location_mapping'],
                    obj=self)
        self.make_header()

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
            self.logger.exception(f'Error fetching PassagePoint authentication token -- {e}')
            raise

    def make_header(self):
        '''Create the HTTP headers, using the PP token.'''
        self.fetch_token()
        self.req_header = {'token': self.token, 'Content-Type': 'application/json'}

    def _extract_id(self, api_data: Dict):
        '''Extracts the visitor ID(s) from the data returned from the createVisitor call.
        api_data should have a top-level key called "data."'''
        #TO DO: Handle situations where more than one data element is returned, if that ever happens.
        if isinstance(api_data, dict):
            api_data = api_data['data']
        id_num = api_data[0]['id']
        return id_num


    def retry(self, func, *args, **kwargs):
        '''Helper function to refresh the token before re-trying the given function.'''
        self.make_header()
        return func(*args, **kwargs)


    def error_handler(self, resp, error, func, *args, **kwargs):
        '''Error handler for HTTP errors. Func should be the function to retry, in case of a 401 error, followed by its arguments and keyword arguments. '''
        if resp.status_code == 401: # Retry if 401
            self.logger.debug('Token expired. Getting new PassagePoint token.')
            self.retry(func, *args, **kwargs)
        else: # Otherwise, log the response and propagate the error
            self.logger.error(f'Error in calling PassagePoint API: {resp.reason}')
            self.logger.error(f'Error response: {resp.text}')
            raise error


    def create_visitor(self, visitor: dict):
        '''Sends a POST request to create a new visitor using a uniqueId'''
        # visitor['user_group'] should correspond to an Alma user group. Default is "Visitor"
        params = {'category': self.user_mapping.get(visitor['user_group'], 'Visitor'),
                  'firstName': visitor['firstName'],
                  'lastName': visitor['lastName'],
                  'email': visitor['email'],
                  'mobilePhoneNo': visitor['primary_id'],
                  'uniqueId': str(visitor['barcode'])}
        try:
            resp = requests.post(self.pp_api_root + self.create_visitor_endpt,
                                 headers=self.req_header,
                                 params=params)
            resp.raise_for_status()
            visitor_data = resp.json()
            if 'error' in visitor_data:
                raise Exception(visitor_data)
            return self._extract_id(visitor_data)
        except HTTPError as e:
            if 'ALREADY_EXIST_UNIQUE_ID' in resp.text:
                # If the request fails because the visitor has already been created, try to get the Visitor ID
                self.logger.debug(f'Visitor {visitor["barcode"]} already exists in PassagePoint; getting Visitor ID.')
                return self.get_visitor_bybarcode(visitor['barcode'])
            else:
                self.error_handler(resp, e, self.create_visitor, visitor)
        except Exception as e:
            self.logger.exception(f'Error creating visitor in PassagePoint for barcode {visitor["barcode"]} -- {e}')
            raise


    def get_visitor_bybarcode(self, barcode: str):
        '''Retrieves the visitor ID from PassagePoint for a provided barcode in the visitor's unique ID field.'''
        try:
            params = {'uniqueId': str(barcode)}
            resp = requests.get(self.pp_api_root + self.uniqueId_endpt,
                                headers=self.req_header,
                                params=params)
            resp.raise_for_status()
            visitor_data = resp.json()
            return self._extract_id(visitor_data)
        except HTTPError as e:
                self.error_handler(resp, e, self.get_visitor_bybarcode, barcode)
        except Exception as e:
            self.logger.exception(f'Error getting visitor from PassagePoint with barcode {barcode} -- {e}')
            raise


    def create_prereg(self, booking: dict, visitor: str):
        '''Creates a Pre-Registration with the visitor ID and LibCal data.
        Requires a booking dict with a visitorId, startTime and endTime
        '''
        try:
            prereg = {}
            format_str = '%Y-%m-%dT%H:%M:%S%z'
            prereg["startTime"] = str(int(datetime.strptime(booking['startTime'], format_str).timestamp()))
            prereg["endTime"] = str(int(datetime.strptime(booking['endTime'], format_str).timestamp()))
            prereg["visitorId"] = str(visitor)
            # Map the LibCal location ID to its destination name in PassagePoint
            prereg["destination"] = self.location_mapping.get(booking['destination'])  # needs to exist in PP
            resp = requests.post(self.pp_api_root + self.create_prereg_endpt,
                                 headers=self.req_header,
                                 json=prereg)
            resp.raise_for_status()
            prereg_data = resp.json()
            if 'error' in prereg_data:
                raise Exception(prereg_data)
            return self._extract_id(prereg_data)
        except HTTPError as e:
            self.error_handler(resp, e, self.create_prereg, booking, visitor)
        except Exception as e:
            self.logger.exception(f'Error creating pre-registration for booking {booking} -- {e}')
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
            self.logger.exception(f'Error getting PassagePoint destinations -- {e}')
            raise


if __name__ == '__main__':
    config = load_config('config.yml')
    passagept = PassagePointRequests(config)
    print(passagept.token)
    print(passagept.req_header)
 #   visitor_data = passagept.create_visitor({'firstName': 'Test',
 #                                            'lastName': 'Patron',
 #                                            'barcode': '012301230123012301'})
 #   print(visitor_data)
    prereg = passagept.create_prereg({"startTime": "2020-08-22T20:05:00-04:00", "endTime": "2020-08-22T22:05:00-04:00", "destination": 8827}, '137505764541138')
    print(prereg)
