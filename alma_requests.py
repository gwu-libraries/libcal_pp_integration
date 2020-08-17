import asyncio
import aiohttp
from aiohttp import ClientResponseError 
from utils import load_config, partition
from asyncio_throttle import Throttler
from typing import List


class AlmaRequests():

    def __init__(self, config_path: str):
        '''config_path should be a path to a config file in YAML format. Config should contain the API key for the Alma Users API as well as the endpoint for looking up a user by Primary ID. '''
        load_config(config_path=config_path, 
                    top_level_key='Alma', 
                    config_keys=['apikey', 'users_endpt'],
                    obj=self)
        # Create request header
        self.headers = {'Authorization': f"apikey {self.apikey}",
                        'Accept': 'application/json'}
        # Initialize throttler for Alma's rate limit
        self.throttler = Throttler(rate_limit=25)

    def _extract_barcodes(self, users: List):
        '''Given a list of user objects, extract a mapping from primary ID to barcode.'''
        mapping = {}
        for user in users:
            primary_id = user['primary_id']
            idents = user['user_identifier']
            for ident in idents:    # Each user has more than one identifier
                if ident['id_type']['value'] == 'BARCODE':
                    barcode = ident['value']
                    mapping[primary_id] = barcode
                    break # Once we've found the barcode, move to the next user
        return mapping

    def main(self, user_ids: List[str]):
        '''Function to run async loop. Argument should be a list of user IDs to retrieve in Alma.'''
        results = asyncio.run(self._retrieve_user_records(user_ids))
        # Valid results have the record_type key
        errors, results = partition(lambda x: 'record_type' in x, results)
        # Extract barcodes as mapping to user IDs
        barcodes = self._extract_barcodes(results)
        print(f'Errors: {list(errors)}') # TO DO: log these somewhere
        return barcodes


    async def _retrieve_user_records(self, user_ids: List[str]):
        '''Given a list of user IDs, retrieve the barcodes from Alma. Async method that gathers calls to fetch_user concurrently.'''
        async with aiohttp.ClientSession() as client:
            queries = [self._fetch_user(user_id, client) for user_id in user_ids]
            results =  await asyncio.gather(*queries, return_exceptions=True)
        return results

    async def _fetch_user(self, user_id: str, client):
        '''Given a user ID, fetch the user\'s record from the Alma API.
        client should be an open aiohttp.CLientSessions'''
        url = f'{self.users_endpt}/{user_id}' # Construct the URL for this user
        try:
            async with self.throttler: # Throttler is set to enforce Alma's rate limits
                async with client.get(url, 
                                        headers=self.headers,
                                        raise_for_status=True) as session: # client should be a reference to a shared aiohttp.ClientSession
                    result = await session.json()
                    return result
        # Return exceptions to the asyncio.gather call
        except ClientResponseError as e:
            print(f'Query to Alma API failed on user {user_id}')
            return {'Error Code': e.status, 'User ID': user_id, 
                    'Error Msg': e.message}
        except Exception as e:
            print(f'Query to Alma API failed on user {user_id}')
            return {'Error': e, 'User ID': user_id}






