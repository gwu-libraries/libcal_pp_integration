import pytest
import responses

from libcal_requests import LibCalRequests


@pytest.fixture
def libcal_config():
    return {'LibCal': {'client_id': 000,
                       'client_secret': '1234567c7be467e51fc47157abcdefg',
                       'locations': [{'name': 'Gelman Library Study Spaces', 'id': 1234},
                                     {'name': 'Virginia Science & Technology Campus Library', 'id': 56789}],
                       'credentials_endpt': 'https://booking.library.gwu.edu/1.1/oauth/token',
                       'bookings_endpt': 'https://booking.library.gwu.edu/1.1/space/bookings',
                       'primary_id_field': 'q12505'}
            }


@pytest.fixture
def valid_location():
    return {'name': 'Gelman Library Study Spaces', 'id': 1234}


@pytest.fixture
def mocked_token_response(libcal_config):
    with responses.RequestsMock() as resp:
        resp.add(responses.POST,
                 libcal_config["LibCal"]["credentials_endpt"],
                 json={'access_token': '1234567890', 'expires_in': 3600,
                       'token_type': 'Bearer', 'scope': 'cal_r ev_r ms_r rm_r sp_r sp_w h_r'},
                 status=200)
        yield resp


@pytest.fixture
def mocked_one_loc_bookings_response(libcal_config):
    ''' Mocks responses from credentials and bookings endpoints.
        All bookings from Gelman
    '''
    with responses.RequestsMock() as resp:
        resp.add(responses.POST,
                 libcal_config["LibCal"]["credentials_endpt"],
                 json={'access_token': '1234567890', 'expires_in': 3600,
                       'token_type': 'Bearer', 'scope': 'cal_r ev_r ms_r rm_r sp_r sp_w h_r'},
                 status=200)
        resp.add(responses.GET,
                 libcal_config["LibCal"]["bookings_endpt"] + "?limit=100&lid=1234&formAnswers=1",
                 json=[{'bookId': 'cs_lxjj123',
                        'eid': 71489,
                        'cid': 18578,
                        'lid': 1234,
                        'fromDate': '2020-10-26T13:15:00-04:00',
                        'toDate': '2020-10-26T13:30:00-04:00',
                        'firstName': 'Person0',
                        'lastName': 'Name0',
                        'email': 'person0@gwu.edu',
                        'status': 'Mediated Approved',
                        'seat_id': 68160,
                        'q12505': 'G00000000'},
                       {'bookId': 'cs_r0dYWJiV',
                        'eid': 71489,
                        'cid': 18578,
                        'lid': 1234,
                        'fromDate': '2020-10-26T13:00:00-04:00',
                        'toDate': '2020-10-26T13:15:00-04:00',
                        'firstName': 'Person',
                        'lastName': 'Name',
                        'email': 'person@gwu.edu',
                        'status': 'Cancelled by User',
                        'seat_id': 68162,
                        'q12505': 'G00000001'},
                       {'bookId': 'cs_lxjj8ycJ',
                        'eid': 71489,
                        'cid': 18578,
                        'lid': 1234,
                        'fromDate': '2020-10-26T13:15:00-04:00',
                        'toDate': '2020-10-26T13:30:00-04:00',
                        'firstName': 'Person2',
                        'lastName': 'Name2',
                        'email': 'person2@gwu.edu',
                        'status': 'Mediated Approved',
                        'seat_id': 68162,
                        'q12505': 'G00000002'},
                       {'bookId': 'cs_MdlPJ2Cg',
                        'eid': 75464,
                        'cid': 19869,
                        'lid': 1234,
                        'fromDate': '2020-10-26T12:05:00-04:00',
                        'toDate': '2020-10-26T15:05:00-04:00',
                        'firstName': 'Person3',
                        'lastName': 'Name3',
                        'email': 'person3@gwu.edu',
                        'status': 'Cancelled by System',
                        'seat_id': 15676,
                        'q12505': 'G00000003'}],
                 status=200)
        yield resp


@pytest.fixture
def mocked_all_loc_bookings_response(libcal_config):
    ''' Mocks responses from credentials and bookings endpoints.
        Bookings from all locations in config.
    '''
    with responses.RequestsMock() as resp:
        resp.add(responses.POST,
                 libcal_config["LibCal"]["credentials_endpt"],
                 json={'access_token': '1234567890', 'expires_in': 3600,
                       'token_type': 'Bearer', 'scope': 'cal_r ev_r ms_r rm_r sp_r sp_w h_r'},
                 status=200)
        resp.add(responses.GET,
                 libcal_config["LibCal"]["bookings_endpt"] + "?limit=100&lid=1234&formAnswers=1",
                 json=[{'bookId': 'cs_lxjj123',
                        'eid': 71489,
                        'cid': 18578,
                        'lid': 1234,
                        'fromDate': '2020-10-26T13:15:00-04:00',
                        'toDate': '2020-10-26T13:30:00-04:00',
                        'firstName': 'Person0',
                        'lastName': 'Name0',
                        'email': 'person0@gwu.edu',
                        'status': 'Mediated Approved',
                        'seat_id': 68160,
                        'q12505': 'G00000000'},
                       {'bookId': 'cs_r0dYWJiV',
                        'eid': 71489,
                        'cid': 18578,
                        'lid': 1234,
                        'fromDate': '2020-10-26T13:00:00-04:00',
                        'toDate': '2020-10-26T13:15:00-04:00',
                        'firstName': 'Person',
                        'lastName': 'Name',
                        'email': 'person@gwu.edu',
                        'status': 'Cancelled by User',
                        'seat_id': 68162,
                        'q12505': 'G00000001'},
                       {'bookId': 'cs_lxjj8ycJ',
                        'eid': 71489,
                        'cid': 18578,
                        'lid': 1234,
                        'fromDate': '2020-10-26T13:15:00-04:00',
                        'toDate': '2020-10-26T13:30:00-04:00',
                        'firstName': 'Person2',
                        'lastName': 'Name2',
                        'email': 'person2@gwu.edu',
                        'status': 'Mediated Approved',
                        'seat_id': 68162,
                        'q12505': 'G00000002'},
                       {'bookId': 'cs_MdlPJ2Cg',
                        'eid': 75464,
                        'cid': 19869,
                        'lid': 1234,
                        'fromDate': '2020-10-26T12:05:00-04:00',
                        'toDate': '2020-10-26T15:05:00-04:00',
                        'firstName': 'Person3',
                        'lastName': 'Name3',
                        'email': 'person3@gwu.edu',
                        'status': 'Cancelled by System',
                        'seat_id': 15676,
                        'q12505': 'G00000003'}],
                 status=200)
        resp.add(responses.GET,
                 libcal_config["LibCal"]["bookings_endpt"] + "?limit=100&lid=56789&formAnswers=1",
                 json=[{'bookId': 'cs_lxjj123',
                        'eid': 71489,
                        'cid': 18578,
                        'lid': 56789,
                        'fromDate': '2020-10-26T13:15:00-04:00',
                        'toDate': '2020-10-26T13:30:00-04:00',
                        'firstName': 'Person0',
                        'lastName': 'Name0',
                        'email': 'person0@gwu.edu',
                        'status': 'Cancelled',
                        'seat_id': 68160,
                        'q12505': 'G00000000'},
                       {'bookId': 'cs_lxjj000',
                        'eid': 71489,
                        'cid': 18578,
                        'lid': 56789,
                        'fromDate': '2020-10-26T13:15:00-04:00',
                        'toDate': '2020-10-26T13:30:00-04:00',
                        'firstName': 'Person4',
                        'lastName': 'Name4',
                        'email': 'person0@gwu.edu',
                        'status': 'Mediated Approved',
                        'seat_id': 68160,
                        'q12505': 'G00000004'}],
                 status=200)
        yield resp


def test_fetch_token(mocked_token_response, libcal_config):
    lc = LibCalRequests(libcal_config)
    assert lc.token == '1234567890'


@responses.activate
def test_fetch_token_error(libcal_config):
    responses.add(responses.POST,
                  libcal_config["LibCal"]["credentials_endpt"],
                  json={'error': 'invalid_client', 'error_description': 'The client credentials are invalid'},
                  status=200)
    with pytest.raises(Exception) as err:
        def check_exceptions():
            LibCalRequests(libcal_config)
        check_exceptions()
    assert "Error" in str(err.value)


@responses.activate
def test_fetch_token_httperror(libcal_config):
    responses.add(responses.POST,
                  libcal_config["LibCal"]["credentials_endpt"],
                  status=500)
    with pytest.raises(Exception) as err:
        def check_exceptions():
            LibCalRequests(libcal_config)
        check_exceptions()
    assert "Error" in str(err.value)


@pytest.mark.parametrize("booking_status, expected_result",
                         [('Mediated Approved', True),
                          ('Mediated Denied', False),
                          ('Cancelled by System', False),
                          ('Cancelled by User', False),
                          ('', False)]
                         )
def test_booking_status(booking_status, expected_result, mocked_token_response, libcal_config):
    lc = LibCalRequests(libcal_config)
    assert lc.check_status(booking_status) is expected_result


def test_prepare_bookings_req(mocked_token_response, valid_location, libcal_config):
    lc = LibCalRequests(libcal_config)
    header, params = lc.prepare_bookings_req(valid_location)
    assert header
    assert type(params) == dict
    assert params['lid'] == 1234
    assert type(params['lid']) == int


def test_get_bookings(mocked_one_loc_bookings_response, valid_location, libcal_config):
    lc = LibCalRequests(libcal_config)
    bookings = lc.get_bookings(valid_location)
    assert len(bookings) == 2
    assert bookings[0]["primary_id"] == "G00000000"


def test_retrieve_bookings_by_location(mocked_all_loc_bookings_response, libcal_config):
    lc = LibCalRequests(libcal_config)
    bookings = lc.retrieve_bookings_by_location()
    assert len(bookings) == 3
    assert bookings[0]["primary_id"] == "G00000000"
    assert bookings[2]["primary_id"] == "G00000004"


@responses.activate
def test_retrieve_no_bookings(valid_location, libcal_config):
    responses.add(responses.POST,
                  libcal_config["LibCal"]["credentials_endpt"],
                  json={'access_token': '1234567890', 'expires_in': 3600,
                        'token_type': 'Bearer', 'scope': 'cal_r ev_r ms_r rm_r sp_r sp_w h_r'},
                  status=200)
    responses.add(responses.GET,
                  libcal_config["LibCal"]["bookings_endpt"],
                  json=[],
                  status=200)
    lc = LibCalRequests(libcal_config)
    lc.locations = [valid_location]
    bookings = lc.retrieve_bookings_by_location()
    assert len(bookings) == 0
