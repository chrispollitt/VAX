IDENTIFICATION DIVISION.
PROGRAM-ID. WAXR.
*
* WAXR.SCO -- WAX & TAPE: the 80s vinyl + cassette tracker
*
* Classic DEC COBOL with embedded SQL on DEC Rdb (database WAXDB).
* Precompile+compile with  SQL$PRE/COBOL WAXR  (see BUILD_WAXR.COM).
*
ENVIRONMENT DIVISION.

DATA DIVISION.
WORKING-STORAGE SECTION.
*
* SQL communication area and database attach (logical WAXDB)
    EXEC SQL INCLUDE SQLCA END-EXEC.
    EXEC SQL DECLARE ALIAS FOR FILENAME 'WAXDB' END-EXEC.

* Host variables
    01  H-ARTIST-ID          PIC S9(9) COMP.
    01  H-ARTIST-NAME        PIC X(32).
    01  H-ORIGIN             PIC X(16).
    01  H-HAIR-SCORE         PIC S9(4) COMP.

    01  H-ALBUM-ID           PIC S9(9) COMP.
    01  H-ALBUM-TITLE        PIC X(40).
    01  H-RELEASE-YEAR       PIC S9(4) COMP.
    01  H-RECORD-LABEL       PIC X(20).
    01  H-GENRE              PIC X(16).

    01  H-HOLDING-ID         PIC S9(9) COMP.
    01  H-MEDIA-CODE         PIC X(1).
    01  H-GRADE              PIC X(3).
    01  H-PRICE-CENTS        PIC S9(9) COMP.
    01  H-BOUGHT-YEAR        PIC S9(4) COMP.
    01  H-HOLDING-NOTES      PIC X(40).

    01  H-COUNT              PIC S9(9) COMP.
    01  H-SUM                PIC S9(9) COMP.
    01  H-NEXT-ID            PIC S9(9) COMP.
    01  H-IND                PIC S9(4) COMP.

* Cursors
    EXEC SQL DECLARE C_ARTISTS CURSOR FOR
        SELECT ARTIST_ID, ARTIST_NAME, ORIGIN, HAIR_SCORE
        FROM ARTIST ORDER BY ARTIST_NAME
    END-EXEC.

    EXEC SQL DECLARE C_ALBUMS CURSOR FOR
        SELECT ALBUM_ID, ALBUM_TITLE, RELEASE_YEAR, RECORD_LABEL, GENRE
        FROM ALBUM WHERE ARTIST_ID = :H-ARTIST-ID
        ORDER BY RELEASE_YEAR, ALBUM_TITLE
    END-EXEC.

    EXEC SQL DECLARE C_HOLDINGS CURSOR FOR
        SELECT HOLDING_ID, MEDIA_CODE, GRADE, PRICE_CENTS, BOUGHT_YEAR,
               HOLDING_NOTES
        FROM HOLDING WHERE ALBUM_ID = :H-ALBUM-ID
        ORDER BY HOLDING_ID
    END-EXEC.

    EXEC SQL DECLARE C_ALLALBUMS CURSOR FOR
        SELECT A.ALBUM_ID, A.ALBUM_TITLE, A.RELEASE_YEAR,
               A.RECORD_LABEL, A.GENRE, R.ARTIST_NAME
        FROM ALBUM A, ARTIST R
        WHERE A.ARTIST_ID = R.ARTIST_ID
        ORDER BY A.ALBUM_TITLE, A.RELEASE_YEAR
    END-EXEC.

* Program variables
    01  WS-CHOICE            PIC X(1).
    01  WS-QUIT              PIC X(1) VALUE "N".
    01  WS-EOF               PIC X(1).
    01  WS-EOF2              PIC X(1).
    01  WS-EOF3              PIC X(1).
    01  WS-FOUND             PIC X(1).
    01  WS-MATCH             PIC X(1).
    01  WS-ANSWER            PIC X(1).
    01  WS-ERRFLAG           PIC X(1) VALUE "N".

    01  WS-SEARCH            PIC X(32).
    01  WS-SLEN              PIC 9(2) COMP.
    01  WS-TARGET            PIC X(40).
    01  WS-HITS              PIC 9(4) COMP.
    01  LOWER-ALPHA          PIC X(26)
             VALUE "abcdefghijklmnopqrstuvwxyz".
    01  UPPER-ALPHA          PIC X(26)
             VALUE "ABCDEFGHIJKLMNOPQRSTUVWXYZ".

    01  WS-IN-NAME           PIC X(32).
    01  WS-IN-ORIGIN         PIC X(16).
    01  WS-IN-TITLE          PIC X(40).
    01  WS-IN-LABEL          PIC X(20).
    01  WS-IN-GENRE          PIC X(16).
    01  WS-IN-NOTES          PIC X(40).
    01  WS-IN-YEAR           PIC 9(4).
    01  WS-IN-HAIR           PIC 9(2).
    01  WS-IN-PRICE          PIC 9(4)V99.
    01  WS-IN-MEDIA          PIC X(1).
    01  WS-IN-GRADE          PIC X(3).
    01  WS-TXT               PIC X(12).
    01  WS-VAL               PIC 9(9) COMP.
    01  WS-CENTS             PIC 9(9) COMP.
    01  WS-DIGIT             PIC 9.
    01  WS-K                 PIC 99 COMP.
    01  WS-STOP              PIC X(1).

    01  WS-MSG-LEN           PIC 9(4) COMP.
    01  WS-MSG-BUF           PIC X(160).

    01  WS-N                 PIC 9(4) COMP.
    01  WS-PICK              PIC 9(4) COMP.
    01  WS-I                 PIC 9(4) COMP.
    01  WS-ED4               PIC ZZZ9.
    01  WS-ED-PRICE          PIC $$$,$$9.99.
    01  WS-DOLLARS           PIC 9(7)V99.
    01  WS-HAIR-TOTAL        PIC 9(6) COMP.
    01  WS-AVG-HAIR          PIC 99V9.
    01  WS-ED-HAIR           PIC Z9.9.
    01  WS-NUM-ARTISTS       PIC 9(4) COMP.
    01  WS-NUM-ALBUMS        PIC 9(4) COMP.
    01  WS-NUM-LP            PIC 9(4) COMP.
    01  WS-NUM-TAPE          PIC 9(4) COMP.
    01  WS-NUM-12IN          PIC 9(4) COMP.
    01  WS-NUM-HOLD          PIC 9(4) COMP.
    01  WS-NUM-DOUBLES       PIC 9(4) COMP.
    01  WS-HAIR-BAR          PIC X(10).
    01  WS-MEDIA-NAME        PIC X(12).
    01  WS-GRADE-NAME        PIC X(36).
    01  WS-TIME              PIC 9(8).
    01  WS-TIME-R REDEFINES WS-TIME.
        05  FILLER           PIC 9(6).
        05  WS-HSEC          PIC 9(2).
    01  WS-QIDX              PIC 9(2) COMP.
    01  WS-J                 PIC 9(2) COMP.

* IDs of the holdings listed on screen, for "sell out"
    01  WS-HOLD-IDS.
        05  WS-HOLD-ID       PIC S9(9) COMP OCCURS 30 TIMES.

* Quips picked by the clock.
    01  QUIP-TABLE.
        05  FILLER PIC X(60) VALUE
            "Side B is where the good stuff hides.".
        05  FILLER PIC X(60) VALUE
            "Have you tried turning the Walkman off and on again?".
        05  FILLER PIC X(60) VALUE
            "Be kind, rewind.".
        05  FILLER PIC X(60) VALUE
            "Mixtapes: the original playlist, with 100% more hiss.".
        05  FILLER PIC X(60) VALUE
            "Big hair, bigger synths, biggest shoulder pads.".
        05  FILLER PIC X(60) VALUE
            "If it ain't got a gatefold, is it even an album?".
        05  FILLER PIC X(60) VALUE
            "Somewhere, a pencil is still rewinding a cassette.".
        05  FILLER PIC X(60) VALUE
            "Fun fact: the 12-inch remix is never shorter.".
    01  QUIP-R REDEFINES QUIP-TABLE.
        05  QUIP             PIC X(60) OCCURS 8 TIMES.

PROCEDURE DIVISION.
MAIN-PARA.
    PERFORM SHOW-BANNER.
    PERFORM MENU-LOOP UNTIL WS-QUIT = "Y".
    EXEC SQL COMMIT END-EXEC.
    PERFORM SHOW-QUIP.
    DISPLAY " ".
    DISPLAY "  Ejecting... please return the tape to its case.".
    DISPLAY "  Thanks for keeping it analog, you magnificent".
    DISPLAY "  hoarder.".
    STOP RUN.

SHOW-BANNER.
    DISPLAY " ".
    DISPLAY "  ================================================".
    DISPLAY "   W A X   &   T A P E".
    DISPLAY "   the totally tubular 80s collection tracker".
    DISPLAY "   (powered by DEC Rdb, because spreadsheets are".
    DISPLAY "    for people who never owned a perm)".
    DISPLAY "  ================================================".

SHOW-QUIP.
    ACCEPT WS-TIME FROM TIME.
    DIVIDE WS-HSEC BY 8 GIVING WS-J REMAINDER WS-QIDX.
    ADD 1 TO WS-QIDX.
    DISPLAY "  -- " QUIP (WS-QIDX).

MENU-LOOP.
    DISPLAY " ".
    DISPLAY "   1) Roll call   - every artist, album and copy".
    DISPLAY "   2) Who is this - look up an artist".
    DISPLAY "   3) Needle drop - find an album by title".
    DISPLAY "   4) New band    - add an artist".
    DISPLAY "   5) New record  - add an album".
    DISPLAY "   6) Fresh wax   - add a copy (LP, tape, 12in)".
    DISPLAY "   7) Sell out    - remove a copy".
    DISPLAY "   8) Stats for nerds".
    DISPLAY "   0) Eject".
    DISPLAY "  Your pick, music lover: " WITH NO ADVANCING.
    ACCEPT WS-CHOICE.
    EVALUATE WS-CHOICE
        WHEN "1" PERFORM LIST-ALL
        WHEN "2" PERFORM LOOKUP-ARTIST
        WHEN "3" PERFORM FIND-ALBUM
        WHEN "4" PERFORM ADD-ARTIST
        WHEN "5" PERFORM ADD-ALBUM
        WHEN "6" PERFORM ADD-HOLDING
        WHEN "7" PERFORM REMOVE-HOLDING
        WHEN "8" PERFORM SHOW-STATS
        WHEN "0" MOVE "Y" TO WS-QUIT
        WHEN OTHER
            DISPLAY "  That is not on the tracklist."
    END-EVALUATE.

*---------------------------------------------------------------
* Roll call: artists -> albums -> holdings
*---------------------------------------------------------------
LIST-ALL.
    MOVE ZERO TO WS-N.
    PERFORM OPEN-ARTISTS.
    PERFORM FETCH-ARTIST.
    PERFORM UNTIL WS-EOF = "Y"
        PERFORM SHOW-ARTIST-FULL
        ADD 1 TO WS-N
        PERFORM FETCH-ARTIST
    END-PERFORM.
    EXEC SQL CLOSE C_ARTISTS END-EXEC.
    IF WS-N = 0
        DISPLAY "  The shelf is bare. A tragedy in three acts."
    ELSE
        DISPLAY " "
        PERFORM SHOW-QUIP
    END-IF.

OPEN-ARTISTS.
    MOVE "N" TO WS-EOF.
    EXEC SQL OPEN C_ARTISTS END-EXEC.
    IF SQLCODE LESS THAN ZERO PERFORM SQL-ERROR.

FETCH-ARTIST.
    EXEC SQL FETCH C_ARTISTS INTO :H-ARTIST-ID, :H-ARTIST-NAME,
        :H-ORIGIN, :H-HAIR-SCORE END-EXEC.
    IF SQLCODE = 100
        MOVE "Y" TO WS-EOF
    ELSE
        IF SQLCODE LESS THAN ZERO
            PERFORM SQL-ERROR
            MOVE "Y" TO WS-EOF
        END-IF
    END-IF.

SHOW-ARTIST-FULL.
    PERFORM MAKE-HAIR-BAR.
    DISPLAY " ".
    DISPLAY "  * " H-ARTIST-NAME " (" H-ORIGIN ")  hair " WS-HAIR-BAR.
    MOVE "N" TO WS-EOF2.
    EXEC SQL OPEN C_ALBUMS END-EXEC.
    PERFORM FETCH-ALBUM-OF-ARTIST.
    PERFORM UNTIL WS-EOF2 = "Y"
        PERFORM SHOW-ALBUM-LINE
        PERFORM SHOW-COPIES
        PERFORM FETCH-ALBUM-OF-ARTIST
    END-PERFORM.
    EXEC SQL CLOSE C_ALBUMS END-EXEC.

FETCH-ALBUM-OF-ARTIST.
    EXEC SQL FETCH C_ALBUMS INTO :H-ALBUM-ID, :H-ALBUM-TITLE,
        :H-RELEASE-YEAR, :H-RECORD-LABEL, :H-GENRE END-EXEC.
    IF SQLCODE = 100
        MOVE "Y" TO WS-EOF2
    ELSE
        IF SQLCODE LESS THAN ZERO
            PERFORM SQL-ERROR
            MOVE "Y" TO WS-EOF2
        END-IF
    END-IF.

SHOW-ALBUM-LINE.
    MOVE H-RELEASE-YEAR TO WS-IN-YEAR.
    DISPLAY "      " WS-IN-YEAR "  " H-ALBUM-TITLE
            " [" H-RECORD-LABEL "]".

* Lists the copies of the album whose id is in H-ALBUM-ID
SHOW-COPIES.
    MOVE "N" TO WS-EOF3.
    EXEC SQL OPEN C_HOLDINGS END-EXEC.
    PERFORM FETCH-HOLDING.
    PERFORM UNTIL WS-EOF3 = "Y"
        PERFORM SHOW-COPY-LINE
        PERFORM FETCH-HOLDING
    END-PERFORM.
    EXEC SQL CLOSE C_HOLDINGS END-EXEC.

FETCH-HOLDING.
    EXEC SQL FETCH C_HOLDINGS INTO :H-HOLDING-ID, :H-MEDIA-CODE,
        :H-GRADE, :H-PRICE-CENTS, :H-BOUGHT-YEAR,
        :H-HOLDING-NOTES END-EXEC.
    IF SQLCODE = 100
        MOVE "Y" TO WS-EOF3
    ELSE
        IF SQLCODE LESS THAN ZERO
            PERFORM SQL-ERROR
            MOVE "Y" TO WS-EOF3
        END-IF
    END-IF.

SHOW-COPY-LINE.
    PERFORM DECODE-MEDIA.
    PERFORM DECODE-GRADE.
    COMPUTE WS-DOLLARS = H-PRICE-CENTS / 100.
    MOVE WS-DOLLARS TO WS-ED-PRICE.
    MOVE H-BOUGHT-YEAR TO WS-IN-YEAR.
    DISPLAY "            - " WS-MEDIA-NAME " " H-GRADE " "
            WS-ED-PRICE " (" WS-IN-YEAR ") " WS-GRADE-NAME.
    IF H-HOLDING-NOTES NOT = SPACES
        DISPLAY "              " QUOTE H-HOLDING-NOTES QUOTE
    END-IF.

MAKE-HAIR-BAR.
    MOVE ALL "." TO WS-HAIR-BAR.
    IF H-HAIR-SCORE > 10
        MOVE 10 TO WS-I
    ELSE
        MOVE H-HAIR-SCORE TO WS-I
    END-IF.
    IF WS-I > 0
        MOVE ALL "#" TO WS-HAIR-BAR (1:WS-I)
    END-IF.

DECODE-MEDIA.
    EVALUATE H-MEDIA-CODE
        WHEN "L" MOVE "12in LP     " TO WS-MEDIA-NAME
        WHEN "C" MOVE "Cassette    " TO WS-MEDIA-NAME
        WHEN "S" MOVE "12in single " TO WS-MEDIA-NAME
        WHEN "7" MOVE "7in single  " TO WS-MEDIA-NAME
        WHEN OTHER MOVE "Mystery disc" TO WS-MEDIA-NAME
    END-EVALUATE.

DECODE-GRADE.
    EVALUATE H-GRADE
        WHEN "M  " MOVE "Mint. Never played, you monster."
                        TO WS-GRADE-NAME
        WHEN "NM " MOVE "Near mint. Handled with oven mitts."
                        TO WS-GRADE-NAME
        WHEN "VG+" MOVE "Played. Loved. Cared for."
                        TO WS-GRADE-NAME
        WHEN "VG " MOVE "Pops a bit. Authentic!"
                        TO WS-GRADE-NAME
        WHEN "G  " MOVE "Well-loved (read: thrashed)."
                        TO WS-GRADE-NAME
        WHEN "F  " MOVE "Fair. Plays like a bag of crisps."
                        TO WS-GRADE-NAME
        WHEN "P  " MOVE "Poor. Sentimental value only."
                        TO WS-GRADE-NAME
        WHEN OTHER MOVE "Grade unknown. Spooky." TO WS-GRADE-NAME
    END-EVALUATE.

*---------------------------------------------------------------
* Search helpers (case-insensitive, partial match)
*---------------------------------------------------------------
GET-SEARCH.
    ACCEPT WS-SEARCH.
    INSPECT WS-SEARCH CONVERTING LOWER-ALPHA TO UPPER-ALPHA.
    MOVE 32 TO WS-SLEN.
    PERFORM UNTIL WS-SLEN = 0
               OR WS-SEARCH (WS-SLEN:1) NOT = SPACE
        SUBTRACT 1 FROM WS-SLEN
    END-PERFORM.

MATCH-CHECK.
    MOVE "N" TO WS-MATCH.
    INSPECT WS-TARGET CONVERTING LOWER-ALPHA TO UPPER-ALPHA.
    IF WS-SLEN = 0
        MOVE "Y" TO WS-MATCH
    ELSE
        MOVE ZERO TO WS-HITS
        INSPECT WS-TARGET TALLYING WS-HITS
            FOR ALL WS-SEARCH (1:WS-SLEN)
        IF WS-HITS > 0
            MOVE "Y" TO WS-MATCH
        END-IF
    END-IF.

*---------------------------------------------------------------
* 2) Look up artists matching a fragment
*---------------------------------------------------------------
LOOKUP-ARTIST.
    DISPLAY "  Name (or a chunk of it, Enter = everyone): "
            WITH NO ADVANCING.
    PERFORM GET-SEARCH.
    MOVE ZERO TO WS-N.
    PERFORM OPEN-ARTISTS.
    PERFORM FETCH-ARTIST.
    PERFORM UNTIL WS-EOF = "Y"
        MOVE H-ARTIST-NAME TO WS-TARGET
        PERFORM MATCH-CHECK
        IF WS-MATCH = "Y"
            ADD 1 TO WS-N
            PERFORM SHOW-ARTIST-FULL
        END-IF
        PERFORM FETCH-ARTIST
    END-PERFORM.
    EXEC SQL CLOSE C_ARTISTS END-EXEC.
    IF WS-N = 0
        DISPLAY "  Never heard of 'em. (Neither has the database.)"
    END-IF.

* Walk the artists asking Y/N on each match; WS-FOUND = "Y" and
* H-ARTIST-ID hold the chosen one.
PICK-ARTIST.
    MOVE "N" TO WS-FOUND.
    DISPLAY "  Artist (name or chunk): " WITH NO ADVANCING.
    PERFORM GET-SEARCH.
    PERFORM OPEN-ARTISTS.
    PERFORM FETCH-ARTIST.
    PERFORM UNTIL WS-EOF = "Y" OR WS-FOUND = "Y"
        MOVE H-ARTIST-NAME TO WS-TARGET
        PERFORM MATCH-CHECK
        IF WS-MATCH = "Y"
            DISPLAY "  Is it " H-ARTIST-NAME "? (Y/N) "
                    WITH NO ADVANCING
            ACCEPT WS-ANSWER
            IF WS-ANSWER = "Y" OR WS-ANSWER = "y"
                MOVE "Y" TO WS-FOUND
            END-IF
        END-IF
        IF WS-FOUND NOT = "Y"
            PERFORM FETCH-ARTIST
        END-IF
    END-PERFORM.
    EXEC SQL CLOSE C_ARTISTS END-EXEC.
    IF WS-FOUND NOT = "Y"
        DISPLAY "  No artist selected. Awkward silence."
    END-IF.

* Same for albums (across everyone, A-Z by title); H-ALBUM-ID holds it.
PICK-ALBUM.
    MOVE "N" TO WS-FOUND.
    DISPLAY "  Album title (or chunk): " WITH NO ADVANCING.
    PERFORM GET-SEARCH.
    MOVE "N" TO WS-EOF.
    EXEC SQL OPEN C_ALLALBUMS END-EXEC.
    PERFORM FETCH-ANY-ALBUM.
    PERFORM UNTIL WS-EOF = "Y" OR WS-FOUND = "Y"
        MOVE H-ALBUM-TITLE TO WS-TARGET
        PERFORM MATCH-CHECK
        IF WS-MATCH = "Y"
            PERFORM SHOW-ALBUM-AND-ARTIST
            DISPLAY "  This one? (Y/N) " WITH NO ADVANCING
            ACCEPT WS-ANSWER
            IF WS-ANSWER = "Y" OR WS-ANSWER = "y"
                MOVE "Y" TO WS-FOUND
            END-IF
        END-IF
        IF WS-FOUND NOT = "Y"
            PERFORM FETCH-ANY-ALBUM
        END-IF
    END-PERFORM.
    EXEC SQL CLOSE C_ALLALBUMS END-EXEC.
    IF WS-FOUND NOT = "Y"
        DISPLAY "  No album selected. Rewind and retry."
    END-IF.

FETCH-ANY-ALBUM.
    EXEC SQL FETCH C_ALLALBUMS INTO :H-ALBUM-ID, :H-ALBUM-TITLE,
        :H-RELEASE-YEAR, :H-RECORD-LABEL, :H-GENRE,
        :H-ARTIST-NAME END-EXEC.
    IF SQLCODE = 100
        MOVE "Y" TO WS-EOF
    ELSE
        IF SQLCODE LESS THAN ZERO
            PERFORM SQL-ERROR
            MOVE "Y" TO WS-EOF
        END-IF
    END-IF.

SHOW-ALBUM-AND-ARTIST.
    MOVE H-RELEASE-YEAR TO WS-IN-YEAR.
    MOVE WS-IN-YEAR TO WS-ED4.
    DISPLAY "  " H-ALBUM-TITLE " (" WS-ED4 ") by " H-ARTIST-NAME.

*---------------------------------------------------------------
* 3) Needle drop: find albums by title fragment
*---------------------------------------------------------------
FIND-ALBUM.
    DISPLAY "  Title (or chunk, Enter = all): " WITH NO ADVANCING.
    PERFORM GET-SEARCH.
    MOVE ZERO TO WS-N.
    MOVE "N" TO WS-EOF.
    EXEC SQL OPEN C_ALLALBUMS END-EXEC.
    PERFORM FETCH-ANY-ALBUM.
    PERFORM UNTIL WS-EOF = "Y"
        MOVE H-ALBUM-TITLE TO WS-TARGET
        PERFORM MATCH-CHECK
        IF WS-MATCH = "Y"
            ADD 1 TO WS-N
            PERFORM SHOW-ALBUM-AND-ARTIST
            PERFORM SHOW-COPIES
        END-IF
        PERFORM FETCH-ANY-ALBUM
    END-PERFORM.
    EXEC SQL CLOSE C_ALLALBUMS END-EXEC.
    IF WS-N = 0
        DISPLAY "  Not in the crates. Time to go digging."
    END-IF.

*---------------------------------------------------------------
* 4) New band
*---------------------------------------------------------------
ADD-ARTIST.
    DISPLAY "  Band / artist name: " WITH NO ADVANCING.
    ACCEPT WS-IN-NAME.
    DISPLAY "  Where from? (e.g. UK, USA, Sweden): "
            WITH NO ADVANCING.
    ACCEPT WS-IN-ORIGIN.
    DISPLAY "  Hair score 0-10 (10 = visible from orbit): "
            WITH NO ADVANCING.
    ACCEPT WS-TXT.
    PERFORM PARSE-INT.
    IF WS-VAL > 10
        MOVE 10 TO WS-IN-HAIR
    ELSE
        MOVE WS-VAL TO WS-IN-HAIR
    END-IF.
    EXEC SQL SELECT MAX(ARTIST_ID) INTO :H-NEXT-ID:H-IND
        FROM ARTIST END-EXEC.
    IF H-IND < 0 MOVE ZERO TO H-NEXT-ID.
    ADD 1 TO H-NEXT-ID.
    MOVE H-NEXT-ID   TO H-ARTIST-ID.
    MOVE WS-IN-NAME   TO H-ARTIST-NAME.
    MOVE WS-IN-ORIGIN TO H-ORIGIN.
    MOVE WS-IN-HAIR   TO H-HAIR-SCORE.
    EXEC SQL INSERT INTO ARTIST
        VALUES (:H-ARTIST-ID, :H-ARTIST-NAME, :H-ORIGIN,
                :H-HAIR-SCORE) END-EXEC.
    PERFORM FINISH-UPDATE.
    IF WS-ERRFLAG = "N"
        DISPLAY "  Welcome to the shelf, " WS-IN-NAME "."
    END-IF.

*---------------------------------------------------------------
* 5) New record
*---------------------------------------------------------------
ADD-ALBUM.
    PERFORM PICK-ARTIST.
    IF WS-FOUND = "Y"
        DISPLAY "  Album title: " WITH NO ADVANCING
        ACCEPT WS-IN-TITLE
        DISPLAY "  Release year (19xx): " WITH NO ADVANCING
        ACCEPT WS-TXT
        PERFORM PARSE-INT
        MOVE WS-VAL TO WS-IN-YEAR
        DISPLAY "  Label: " WITH NO ADVANCING
        ACCEPT WS-IN-LABEL
        DISPLAY "  Genre (New Wave, Synthpop, Hair Metal...): "
                WITH NO ADVANCING
        ACCEPT WS-IN-GENRE
        EXEC SQL SELECT MAX(ALBUM_ID) INTO :H-NEXT-ID:H-IND
            FROM ALBUM END-EXEC
        IF H-IND < 0 MOVE ZERO TO H-NEXT-ID END-IF
        ADD 1 TO H-NEXT-ID
        MOVE H-NEXT-ID    TO H-ALBUM-ID
        MOVE WS-IN-TITLE  TO H-ALBUM-TITLE
        MOVE WS-IN-YEAR   TO H-RELEASE-YEAR
        MOVE WS-IN-LABEL  TO H-RECORD-LABEL
        MOVE WS-IN-GENRE  TO H-GENRE
        EXEC SQL INSERT INTO ALBUM
            VALUES (:H-ALBUM-ID, :H-ARTIST-ID, :H-ALBUM-TITLE,
                    :H-RELEASE-YEAR, :H-RECORD-LABEL, :H-GENRE)
        END-EXEC
        PERFORM FINISH-UPDATE
        IF WS-ERRFLAG = "N"
            DISPLAY "  Filed under cool."
        END-IF
    END-IF.

*---------------------------------------------------------------
* 6) Fresh wax: add a copy of an album
*---------------------------------------------------------------
ADD-HOLDING.
    PERFORM PICK-ALBUM.
    IF WS-FOUND = "Y"
        DISPLAY "  Format: L)P  C)assette  S)12in single  "
                "7)7in single: " WITH NO ADVANCING
        ACCEPT WS-IN-MEDIA
        INSPECT WS-IN-MEDIA CONVERTING LOWER-ALPHA TO UPPER-ALPHA
        DISPLAY "  Condition (M NM VG+ VG G F P): "
                WITH NO ADVANCING
        ACCEPT WS-IN-GRADE
        INSPECT WS-IN-GRADE CONVERTING LOWER-ALPHA TO UPPER-ALPHA
        DISPLAY "  Price paid, dollars (e.g. 8.99): "
                WITH NO ADVANCING
        ACCEPT WS-TXT
        PERFORM PARSE-MONEY
        MOVE WS-VAL TO WS-CENTS
        DISPLAY "  Year bought: " WITH NO ADVANCING
        ACCEPT WS-TXT
        PERFORM PARSE-INT
        MOVE WS-VAL TO WS-IN-YEAR
        DISPLAY "  Notes (where? who? why?): " WITH NO ADVANCING
        ACCEPT WS-IN-NOTES
        EXEC SQL SELECT MAX(HOLDING_ID) INTO :H-NEXT-ID:H-IND
            FROM HOLDING END-EXEC
        IF H-IND < 0 MOVE ZERO TO H-NEXT-ID END-IF
        ADD 1 TO H-NEXT-ID
        MOVE H-NEXT-ID   TO H-HOLDING-ID
        MOVE WS-IN-MEDIA TO H-MEDIA-CODE
        MOVE WS-IN-GRADE TO H-GRADE
        MOVE WS-CENTS    TO H-PRICE-CENTS
        MOVE WS-IN-YEAR  TO H-BOUGHT-YEAR
        MOVE WS-IN-NOTES TO H-HOLDING-NOTES
        EXEC SQL INSERT INTO HOLDING
            VALUES (:H-HOLDING-ID, :H-ALBUM-ID, :H-MEDIA-CODE,
                    :H-GRADE, :H-PRICE-CENTS, :H-BOUGHT-YEAR,
                    :H-HOLDING-NOTES)
        END-EXEC
        PERFORM FINISH-UPDATE
        IF WS-ERRFLAG = "N"
            DISPLAY "  Another one for the pile. Respect."
        END-IF
    END-IF.

*---------------------------------------------------------------
* 7) Sell out: delete one holding
*---------------------------------------------------------------
REMOVE-HOLDING.
    PERFORM PICK-ALBUM.
    IF WS-FOUND = "Y"
        MOVE ZERO TO WS-N
        MOVE "N" TO WS-EOF3
        EXEC SQL OPEN C_HOLDINGS END-EXEC
        PERFORM FETCH-HOLDING
        PERFORM UNTIL WS-EOF3 = "Y" OR WS-N = 30
            ADD 1 TO WS-N
            MOVE H-HOLDING-ID TO WS-HOLD-ID (WS-N)
            MOVE WS-N TO WS-ED4
            PERFORM DECODE-MEDIA
            DISPLAY "   " WS-ED4 ") " WS-MEDIA-NAME " " H-GRADE
                    " " H-HOLDING-NOTES
            PERFORM FETCH-HOLDING
        END-PERFORM
        EXEC SQL CLOSE C_HOLDINGS END-EXEC
        IF WS-N = 0
            DISPLAY "  You own none of those. Can't sell air."
        ELSE
            DISPLAY "  Which copy goes to the record fair? "
                    "(number, 0 = keep all): " WITH NO ADVANCING
            ACCEPT WS-TXT
            PERFORM PARSE-INT
            MOVE WS-VAL TO WS-PICK
            IF WS-PICK > 0 AND WS-PICK NOT > WS-N
                MOVE WS-HOLD-ID (WS-PICK) TO H-HOLDING-ID
                EXEC SQL DELETE FROM HOLDING
                    WHERE HOLDING_ID = :H-HOLDING-ID END-EXEC
                PERFORM FINISH-UPDATE
                IF WS-ERRFLAG = "N"
                    DISPLAY "  Sold. Cash in hand, hole in heart."
                END-IF
            ELSE
                DISPLAY "  Wise. Never sell the hits."
            END-IF
        END-IF
    END-IF.

*---------------------------------------------------------------
* 8) Stats for nerds
*---------------------------------------------------------------
SHOW-STATS.
    EXEC SQL SELECT COUNT(*) INTO :H-COUNT FROM ARTIST END-EXEC.
    MOVE H-COUNT TO WS-NUM-ARTISTS.
    EXEC SQL SELECT COUNT(*) INTO :H-COUNT FROM ALBUM END-EXEC.
    MOVE H-COUNT TO WS-NUM-ALBUMS.
    EXEC SQL SELECT COUNT(*) INTO :H-COUNT FROM HOLDING END-EXEC.
    MOVE H-COUNT TO WS-NUM-HOLD.
    EXEC SQL SELECT COUNT(*) INTO :H-COUNT FROM HOLDING
        WHERE MEDIA_CODE = 'L' END-EXEC.
    MOVE H-COUNT TO WS-NUM-LP.
    EXEC SQL SELECT COUNT(*) INTO :H-COUNT FROM HOLDING
        WHERE MEDIA_CODE = 'C' END-EXEC.
    MOVE H-COUNT TO WS-NUM-TAPE.
    EXEC SQL SELECT COUNT(*) INTO :H-COUNT FROM HOLDING
        WHERE MEDIA_CODE = 'S' END-EXEC.
    MOVE H-COUNT TO WS-NUM-12IN.
    EXEC SQL SELECT COUNT(*) INTO :H-COUNT FROM ALBUM A
        WHERE (SELECT COUNT(*) FROM HOLDING H
               WHERE H.ALBUM_ID = A.ALBUM_ID) > 1 END-EXEC.
    MOVE H-COUNT TO WS-NUM-DOUBLES.
    EXEC SQL SELECT SUM(PRICE_CENTS) INTO :H-SUM:H-IND
        FROM HOLDING END-EXEC.
    IF H-IND < 0 MOVE ZERO TO H-SUM.
    EXEC SQL SELECT SUM(HAIR_SCORE) INTO :H-COUNT:H-IND
        FROM ARTIST END-EXEC.
    IF H-IND < 0 MOVE ZERO TO H-COUNT.
    MOVE H-COUNT TO WS-HAIR-TOTAL.
    DISPLAY " ".
    DISPLAY "  ---- THE NUMBERS (nerd mode engaged) ----".
    MOVE WS-NUM-ARTISTS TO WS-ED4.
    DISPLAY "  Artists ................ " WS-ED4.
    MOVE WS-NUM-ALBUMS TO WS-ED4.
    DISPLAY "  Albums ................. " WS-ED4.
    MOVE WS-NUM-HOLD TO WS-ED4.
    DISPLAY "  Physical objects ....... " WS-ED4.
    MOVE WS-NUM-LP TO WS-ED4.
    DISPLAY "    12in LPs ............. " WS-ED4.
    MOVE WS-NUM-TAPE TO WS-ED4.
    DISPLAY "    Cassettes ............ " WS-ED4.
    MOVE WS-NUM-12IN TO WS-ED4.
    DISPLAY "    12in singles ......... " WS-ED4.
    MOVE WS-NUM-DOUBLES TO WS-ED4.
    DISPLAY "  Albums owned twice+ .... " WS-ED4.
    COMPUTE WS-DOLLARS = H-SUM / 100.
    MOVE WS-DOLLARS TO WS-ED-PRICE.
    DISPLAY "  Total spent ............ " WS-ED-PRICE.
    IF WS-NUM-ARTISTS > 0
        COMPUTE WS-AVG-HAIR = WS-HAIR-TOTAL / WS-NUM-ARTISTS
        MOVE WS-AVG-HAIR TO WS-ED-HAIR
        DISPLAY "  Average artist hair .... " WS-ED-HAIR " / 10"
        IF WS-AVG-HAIR > 7
            DISPLAY "  Verdict: aerosol-grade. Wear a hard hat."
        ELSE
            IF WS-AVG-HAIR > 4
                DISPLAY "  Verdict: respectable volume."
            ELSE
                DISPLAY "  Verdict: suspiciously well-behaved."
            END-IF
        END-IF
    END-IF.
    IF WS-NUM-TAPE > WS-NUM-LP
        DISPLAY "  More tape than vinyl. Walkman gang rules."
    ELSE
        DISPLAY "  More vinyl than tape. Audiophile alert."
    END-IF.

*---------------------------------------------------------------
* Number parsing from the text in WS-TXT (digits only; a non-digit
* ends the number).  ACCEPT straight into a numeric field chokes on
* things like "9.50", so everything is read as text first.
*---------------------------------------------------------------
PARSE-INT.
    MOVE ZERO TO WS-VAL.
    MOVE "N" TO WS-STOP.
    PERFORM VARYING WS-K FROM 1 BY 1
            UNTIL WS-K > 12 OR WS-STOP = "Y"
        IF WS-TXT (WS-K:1) >= "0" AND WS-TXT (WS-K:1) <= "9"
            MOVE WS-TXT (WS-K:1) TO WS-DIGIT
            COMPUTE WS-VAL = WS-VAL * 10 + WS-DIGIT
        ELSE
            MOVE "Y" TO WS-STOP
        END-IF
    END-PERFORM.

* Dollars[.cents] -> cents in WS-VAL
PARSE-MONEY.
    MOVE ZERO TO WS-VAL.
    MOVE "N" TO WS-STOP.
    MOVE 1 TO WS-K.
    PERFORM UNTIL WS-K > 12 OR WS-STOP = "Y"
        IF WS-TXT (WS-K:1) >= "0" AND WS-TXT (WS-K:1) <= "9"
            MOVE WS-TXT (WS-K:1) TO WS-DIGIT
            COMPUTE WS-VAL = WS-VAL * 10 + WS-DIGIT
            ADD 1 TO WS-K
        ELSE
            MOVE "Y" TO WS-STOP
        END-IF
    END-PERFORM.
    COMPUTE WS-VAL = WS-VAL * 100.
    IF WS-K NOT > 12
        IF WS-TXT (WS-K:1) = "."
            ADD 1 TO WS-K
            IF WS-K NOT > 12
                IF WS-TXT (WS-K:1) >= "0" AND WS-TXT (WS-K:1) <= "9"
                    MOVE WS-TXT (WS-K:1) TO WS-DIGIT
                    COMPUTE WS-VAL = WS-VAL + WS-DIGIT * 10
                    ADD 1 TO WS-K
                    IF WS-K NOT > 12
                        IF WS-TXT (WS-K:1) >= "0"
                           AND WS-TXT (WS-K:1) <= "9"
                            MOVE WS-TXT (WS-K:1) TO WS-DIGIT
                            COMPUTE WS-VAL = WS-VAL + WS-DIGIT
                        END-IF
                    END-IF
                END-IF
            END-IF
        END-IF
    END-IF.

*---------------------------------------------------------------
* Commit an update (or roll it back if the SQL statement failed)
*---------------------------------------------------------------
FINISH-UPDATE.
    MOVE "N" TO WS-ERRFLAG.
    IF SQLCODE LESS THAN ZERO
        MOVE "Y" TO WS-ERRFLAG
        PERFORM SQL-ERROR
        EXEC SQL ROLLBACK END-EXEC
    ELSE
        EXEC SQL COMMIT END-EXEC
        IF SQLCODE LESS THAN ZERO
            MOVE "Y" TO WS-ERRFLAG
            PERFORM SQL-ERROR
        END-IF
    END-IF.

*---------------------------------------------------------------
* Database error: show the SQL status
*---------------------------------------------------------------
SQL-ERROR.
    DISPLAY " ".
    DISPLAY "  Whoa, the database just scratched the record:".
    DISPLAY "  SQLCODE = " SQLCODE.
    CALL "SQL$GET_ERROR_TEXT" USING BY DESCRIPTOR WS-MSG-BUF
                                    BY REFERENCE WS-MSG-LEN.
    IF WS-MSG-LEN > 0 AND WS-MSG-LEN < 161
        DISPLAY "  " WS-MSG-BUF (1:WS-MSG-LEN)
    END-IF.
