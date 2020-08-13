import sqlite3
from sqlite3 import OperationalError, IntegrityError, Row
from typing import Dict, List

class SQLiteCache():

    def __init__(self, db_name: str = 'cache.db'):
        '''Initializes a SQLite database (unless it already exists) with the supplied name (if given).'''
        try:
            self.conn = sqlite3.connect(db_name)
            self.conn.row_factory = Row # Facilitates lookup of query results by key
            self.cursor = self.conn.cursor()
        except Exception as e:
            print('Error connecting to database.')
            raise

        self._create_tables()

    def _create_tables(self):
        '''Initializes database with tables for users and appointments, if these don\'t exist'''
        try:
            with self.conn:
                self.cursor.execute('''
                                CREATE TABLE users 
                                    (primary_id text PRIMARY KEY, barcode text, visitor_id text)
                                ''')
                self.cursor.execute('''
                                    CREATE TABLE appts
                                        (appt_id text PRIMARY KEY, prereg_id text)
                                ''')
        except OperationalError as e:
            # Catch error if table already exists; no need to recreate
            if 'already exists' in e.args[0]:
                print('Tables already exist. Skipping table creation.')
                return
        except Exception as e:
            raise

    def user_lookup(self, primary_id: str):
        '''Retrieve the user\'s data from the database if it exists.'''
        try:
            with self.conn:
                self.cursor.execute('''
                                    SELECT * from users 
                                    WHERE primary_id = :primary_id
                                ''', {'primary_id': primary_id})
                row = self.cursor.fetchone()
            # Convert result to a dictionary
            if row:
                return dict(row)
            return None
        except Exception as e:
            print('Error querying users table.')
            raise

    def appt_lookup(self, appt_id: str):
        '''Queries the appointments table for an existing appointment.
        appt_id should be a LibCal bookId.'''
        try:
            with self.conn:
                self.cursor.execute('''
                                        SELECT * from appts
                                        WHERE appt_id = :appt_id
                                    ''', {'appt_id': appt_id})
                row = self.cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            print('Error querying appointments table.')
            raise

    def add_users(self, user_data: List[Dict]):
        '''Adds users to the users table.
        user_data should be a list of dictionaries, each containing the user\'s Alma primary ID, barcode, and visitor ID (Passage Point).'''
        with self.conn:
            try:
                # Current behavior is to replace rows upon violation of the primary key constraint (on the primary ID.) That might be useful if, for instance, a user's visitor ID in Passage Point somehow changes.
                self.cursor.executemany('''
                                    INSERT OR REPLACE INTO users (primary_id, barcode, visitor_id) 
                                    VALUES (:primary_id, :barcode, :visitor_id)
                                    ''', user_data)
            except Exception as e:
                print(f'Error loading users {user_data}')
                raise

    def add_appt(self, appt_data: Dict):
        '''Insert a single mapping from LibCal to PassagePoint appointment IDs. 
        appt_data should contain appt_id (LibCal) and prereg_id (PP) as keys.'''
        with self.conn:
            try:
                self.cursor.execute('''
                                        INSERT INTO appts (appt_id, prereg_id) 
                                        VALUES (:appt_id, :prereg_id)
                                    ''', appt_data)
            except IntegrityError:
                print(f'Primary key constraint invalid on {appd_data["appt_id"]}. This key is already in the database.')
                raise
            except Exception as e:
                print(f'Error loading appointments {appt_data}.')
                raise 

    def delete_appts(self):
        pass

if __name__ == '__main__':
    sqc = SQLiteCache()
