# libcal_pp_integration
Development repo for API integration between LibCal and Passage Point

1. The endpoint to retrieve the room reservations from LibCal is `https://booking.library.gwu.edu/1.1/space/bookings`. 
2. It's possible to add a specific date as a querystring parameter; otherwise, the default is today's date.
3. It looks as though it's possible to retrieve additional information from the user's request form with the formAnswers parameter; we could test that for obtaining the barcode and GWID.
4. I don't see anything about rate limits. 
5. Limit of results per request is 100, which may be just fine if we're querying as frequently as Jennifer has proposed.
6. I note that the form currently covers spaces in both Gelman and VSTC. Do we need to filter the query/responses only to those locations in Gelman?
