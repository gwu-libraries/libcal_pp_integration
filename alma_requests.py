import asyncio
import aiohttp
from aiohttp import ClientResponseError 
from utils import check_config, partition
from asyncio_throttle import Throttler
from typing import List, Dict
import logging


class AlmaRequests():

    def __init__(self, config: Dict):
        '''config should be a Python dictionary containing the API key for the Alma Users API as well as the endpoint for looking up a user by Primary ID. '''
        self.logger = logging.getLogger('lcpp.alma_requests')
        check_config(config=config,
                    top_level_key='Alma', 
                    config_keys=['apikeys', 'users_endpt'],
                    obj=self)
        # Initialize throttler for Alma's rate limit
        self.throttler = Throttler(rate_limit=25)


    def _extract_info(self, users: List):
        '''Given a list of user objects, extract a mapping from primary ID to barcode.'''
        mapping = {}
        for user in users:
            primary_id = user['primary_id']
            mapping[primary_id] = {'user_group': self._extract_user_group(user)}
            idents = user['user_identifier']
            for ident in idents:    # Each user has more than one identifier
                if ident['id_type']['value'] == 'BARCODE':
                    barcode = ident['value']
                    mapping[primary_id]['barcode'] = barcode
                    break # Once we've found the barcode, move to the next user
        return mapping


    def _extract_user_group(self, user: Dict):
        '''Given a user object, extract the user group.'''
        user_group = user.get('user_group')
        if user_group:
            return user_group.get('desc')
        return user_group


    def main(self, user_ids: List[str]):
        '''Function to run async loop. Argument should be a list of user IDs to retrieve in Alma.'''
        user_data = {}
        # Loop through available Alma API keys in order. Allows querying of multiple IZ's.
        for apikey in self.apikeys:
            # Create request header
            self.headers = {'Authorization': f"apikey {apikey}",
                        'Accept': 'application/json'}
            results = asyncio.run(self._retrieve_user_records(user_ids))
            # Valid results have the record_type key
            errors, results = partition(lambda x: x and 'record_type' in x, results)
            # Extract barcodes and user groups as mapping to user IDs
            user_data.update(self._extract_info(results))
            # Get the remaining user ID's to query
            user_ids = [e['User ID'] for e in errors if e['Error'] == 'User Not Found']
            if not user_ids:
                break
        # Log user ID's that could not be found
        if user_ids:
            self.logger.error(f"Users could not be found in any IZ: {user_ids}")
        return user_data


    async def _retrieve_user_records(self, user_ids: List[str]):
        '''Given a list of user IDs, retrieve the barcodes from Alma. Async method that gathers calls to fetch_user concurrently.'''
        async with aiohttp.ClientSession() as client:
            queries = [self._fetch_user(user_id, client) for user_id in user_ids if user_id]
            results =  await asyncio.gather(*queries, return_exceptions=True)
        return results

    def _check_error_status(self, error_msg: Dict):
        '''Checks an Alma API error message for a "User not found" error.'''
        for error in error_msg['errorList']['error']:
            if error['errorCode'] == '401861':
                return True # Found an instance of user not found

    async def _fetch_user(self, user_id: str, client):
        '''Given a user ID, fetch the user\'s record from the Alma API.
        client should be an open aiohttp.CLientSessions'''
        url = f'{self.users_endpt}/{user_id}' # Construct the URL for this user
        try:
            async with self.throttler: # Throttler is set to enforce Alma's rate limits
                async with client.get(url, 
                                        headers=self.headers,
                                        raise_for_status=False) as session: # client should be a reference to a shared aiohttp.ClientSession
                    if session.status != 200:
                        if session.content_type == 'application/json':
                            body = await session.json()
                            if self._check_error_status(body): # Test for User not found error
                                # Flag this error to query the user in another IZ, if possible
                                return {'Error': 'User Not Found', 'User ID': user_id}
                        else:
                            session.raise_for_status()
                    result = await session.json()
                    return result
        # Return exceptions to the asyncio.gather call
        except ClientResponseError as e:
            self.logger.exception(f'Query to Alma API failed on user {user_id}')
            return {'Error': e.status, 'User ID': user_id, 
                    'Error Msg': e.message}
        except Exception as e:
            self.logger.exception(f'Query to Alma API failed on user {user_id}')
            return {'Error': e, 'User ID': user_id}






