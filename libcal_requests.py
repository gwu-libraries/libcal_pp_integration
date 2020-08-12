import requests
import yaml

class LibCalRequests():

    def __init__(self, config_path: str):
        '''config_path should be a path to a config file in YAML format. Config should contain the client id and client secret for the LibCal API, as well as the authentication and bookings endpoints, all nested under a "LibCal" key. '''

        self.load_config(config_path)
        self.fetch_token()
        print(self.get_bookings())


    def get_bookings(self):
        '''Fetches the space appointments for today\'s date (default).'''
        try:
            headers, params = self.prepare_bookings_req()
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

    def prepare_bookings_req(self):
        '''Creates the authentication header and the default parameters for the LibCal bookings calls.'''
        header = {'Authorization': f'Bearer {self.token}'}
        params = {'limit': 100} # Max value
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
            # Check for errors in the JSON
            if 'error' in token:
                raise Exception(f'Error returned by LibCal authentication API: {token}')
            # Store the access token string
            self.token = token['access_token']
            return self
        except Exception as e:
            print('Error fetching LibCal authentication token.')
            raise

    def load_config(self, config_path: str):
        '''Opens the YAML config file supplied to the __init__ method.'''
        try:
            with open(config_path, 'r') as f:
                config = yaml.load(f, Loader=yaml.FullLoader)
                if 'LibCal' not in config:
                    raise Exception(f'{config} should contain a dictionary of LibCal API settings, stored under the "LibCal" key.')
                config_values = {'client_id', 'client_secret', 'credentials_endpt', 'bookings_endpt'}
                # Test for the presence of the required API settings
                if not config_values <= set(config['LibCal'].keys()):
                    raise Exception(f'One or more LibCal API settings missing from {config_path}')
                # For convenience, convert to class attributes
                for c in config_values:
                    setattr(self, c, config['LibCal'][c])
            return self
        except Exception as e:
            print("Error loading configuration.")
            raise

if __name__ == '__main__':
    libcal = LibCalRequests('config.yml')
