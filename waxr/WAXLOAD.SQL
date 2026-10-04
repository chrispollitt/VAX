-- WAXLOAD.SQL -- create the WAXDB database and load the sample collection.
-- Used by BUILD_WAXR.COM as the input of the interactive SQL session.
@WAXDB
@WAXDATA
SELECT COUNT(*) FROM ARTIST;
SELECT COUNT(*) FROM ALBUM;
SELECT COUNT(*) FROM HOLDING;
EXIT
