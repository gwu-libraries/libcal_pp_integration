# libcal_pp_integration
Development repo for API integration between LibCal and Passage Point

## Application Components
 - `libcal_requests.py`, which contains the `LibCalRequests` class. 
   - On instantiation, pass the name of a config YAML file. (Default is `config.yml`, which should reside in the same directory as the module.)
   - The `__init__` method gets a new auth token (using the supplied paramters in the config.)
   - The `retrieve_bookings` method fetches the day's current bookings for the locations specified in the config.
 - `alma_requests.py`, which contains the `AlmaRequests` class.
   - Instantiation argument is the same as for `LibCalRequests`.
   - Pass the `main` method a Python `list` of Alma Primary ID's (GWID numbers) to return the users' barcodes. Failed matches will be omitted from the returned results.
 - `sqlite_cache.py`, which contains the `SQLiteCache` class.
   - Instantiate with an optional name/path string for the database file.
   - If not present, a new instance creates the `users` and `appts` tables.
   - `add_user` accepts a list of dictionaries of the following structure:
   `{'primary_id': 'GXXXXXXXX',
	'barcode': '2282XXXXXXXXX',
	'visitor_id': 'sdfjh3'}`
	where `visitor_id` corresponds to the `id` returned by the `createVistor` endpoint of the PassagePoint API, and the other values are from Alma.
   - `lookup_user` queries the database for a provided `primary_id` and returns the user's other identifiers (if found).
   - `add_appt` accepts a single Python dictionary of the following structure:
	`{'appt_id': 'yt54884',
	  'prereg_id': '343234jf'}`
	  where `appt_id` corresponds to the `bookId` from the LibCal API, and `prereg_id` corresponds to the `id` returned by the `createPreReg` endpoint in PassagePoint.
   - `lookup_appt` queries the database for a single provided `appt_id` (LibCal's `bookId`) and returns the mapping to the PassagePoint ID.
 - `app.py`, which contains the `LibCal2PP` class. 
   - `__init__` creates instances of the `AlmaRequests`, `LibCalRequests`, and `SQLiteCache` classes.
   - `log_new_bookings` does the following:
     1. Fetch space bookings from LibCal.
     2. Filter out those that are already in the SQL cache. (These will already have been registered with PassagePoint.)
     3. Calls `process_users` to obtain the PassagePoint VisitorId's.
     4. Creates PassagePoint metadata for new pre-registrations, using the LibCal booking data and the PassagePoint VisitorId.
     5. **Not Yet Implemented** Makes a call to `PassagePointRequests` to create each pre-reg.
     6. Records these pre-regs in the SQL cache.
  - `process_users` does the following:
    1. Separates the users with new LibCal appointments into those already in the SQL cache (users with PassagePoint accounts) and those needing to have accounts created.
    2. Calls `register_new_users` to create the PassagePoint accounts.
    3. Saves these users in the SQL cache.
    4. Returns the VisitorId's for all users.
  - `register_new_users` does the following:
    1. Retrieve barcodes for new users from Alma, using the Primary Id (GWID) from the LibCal appointment.
    2. **Not Yet Implemented** Calls the appropriate method in `PassagePointRequests` to create a new user account and return the VisitorId for each new user.


## Not Yet Implemented

1. **Done** Exception handling currently just prints to `stdout`. Need to add logging.
2. Need to handle requests to PassagePoint to do the following:
   - Create new visitors.
   - Create new pre-registrations.
3. Need to implement logic to tie the components together as follows:
   - **Done** On startup, instantiate the SQLite db.
   - **Done** Query the LibCal API (`LibCalRequests.retrieve_bookings`).
   - **Done** Filter for appointments already in the db (`SQLiteCache.appt_lookup`).
   - **Done** For each user with a new appointment:
     - Retrieve `visitor_id` if already in the db (`SQLiteCache.lookup_user`).
   - For users not in the db:
     - **Done** Get their barcodes from Alma (`AlmaRequests.main`) -- can be done in bulk.
     - Create users in PassagePoint.
     - Save new user mappings to the db (`SQLiteCache.add_users`).
   - For each new appointment:
     - Create the prereg in PassagePoint.
     - Save the appointment mapping to the db (`SQLiteCache.add_appt`).
4. If running all of the above in a loop, we may need logic to check for an expire auth token for LibCal and PassagePoint. 
   - For LibCal, it might be easiest just to get a new token before each call to the bookings API. (`LibCalRequests` is currently written to do so on init).
   - Not sure about PassagePoint.
5. Add a method to `app.py` to run the process at specified intervals.
6. To keep the size of the db in check, we may want periodically to delete rows with past appointments. We could implement by adding a timestamp column. 
