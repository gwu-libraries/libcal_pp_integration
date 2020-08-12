import argparse
from alma_requests import AlmaRequests


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Process some GWIDs.')
	parser.add_argument('users', nargs='+')
	user_ids = parser.parse_args().users
	ar = AlmaRequests('config.yml')
	results = ar.main(user_ids)
	print(f'Results: {results}')


