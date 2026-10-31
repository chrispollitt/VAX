"""Sample 80s collection for WAXR: the data table used by gen_sql.py.

Each entry: (artist, origin, hair score 0-10,
             [(album, year, label, genre,
               [(media, grade, price_cents, year_bought, notes), ...]), ...])
Media: L = 12in LP, C = cassette, S = 12in single, 7 = 7in single.
"""

# (artist, origin, hair, [ (title, year, label, genre, [ (media, grade, cents, bought, notes), ... ]) ])
DATA = [
 ("Duran Duran", "UK", 10, [
   ("Rio", 1982, "EMI", "New Romantic", [
     ("L", "VG+", 899, 1983, "Bought with lawn-mowing money"),
     ("C", "VG ", 799, 1984, "Wore out the B-side. Both sides."),
   ]),
   ("Seven and the Ragged Tiger", 1983, "EMI", "Synthpop", [
     ("C", "G  ", 799, 1984, "Chewed by the Walkman. Sorry Simon."),
   ]),
   ("Notorious", 1986, "EMI", "Synthpop", [
     ("L", "NM ", 999, 1986, "Day-one purchase. Stood in line."),
   ]),
 ]),
 ("Depeche Mode", "UK", 7, [
   ("Some Great Reward", 1984, "Mute", "Synthpop", [
     ("L", "VG ", 899, 1985, "Blasphemous Rumours on repeat"),
   ]),
   ("Black Celebration", 1986, "Mute", "Synthpop", [
     ("L", "VG+", 999, 1986, "Cheerful. As always."),
     ("C", "VG ", 799, 1987, "Car tape, ran hot, still plays"),
   ]),
   ("Music for the Masses", 1987, "Mute", "Synthpop", [
     ("L", "NM ", 999, 1987, "Imported. Felt very continental."),
   ]),
 ]),
 ("The Cure", "UK", 9, [
   ("Pornography", 1982, "Fiction", "Goth", [
     ("L", "VG ", 899, 1984, "Do not play on a sunny day"),
   ]),
   ("The Head on the Door", 1985, "Fiction", "Alternative", [
     ("C", "VG+", 799, 1985, "In Between Days = summer 85"),
   ]),
   ("Disintegration", 1989, "Fiction", "Goth", [
     ("L", "NM ", 1099, 1989, "Double LP. Sat in the dark. Obviously."),
     ("C", "VG ", 899, 1989, "For the bus. Cried on the 42."),
   ]),
 ]),
 ("Prince", "USA", 8, [
   ("Purple Rain", 1984, "Warner Bros.", "Funk Rock", [
     ("L", "VG+", 899, 1984, "Saw the movie twice first"),
     ("C", "VG ", 799, 1985, "Replacement; the first one melted"),
   ]),
   ("Sign o' the Times", 1987, "Paisley Park", "Funk", [
     ("L", "NM ", 1299, 1987, "Double LP. Worth every penny."),
   ]),
 ]),
 ("Michael Jackson", "USA", 8, [
   ("Thriller", 1982, "Epic", "Pop", [
     ("L", "G  ", 899, 1983, "Everyone owned it. Everyone."),
     ("C", "VG ", 799, 1983, "Dance routine rehearsed in the garage"),
   ]),
   ("Bad", 1987, "Epic", "Pop", [
     ("C", "VG+", 899, 1987, "Shamone."),
   ]),
 ]),
 ("Madonna", "USA", 9, [
   ("Like a Virgin", 1984, "Sire", "Pop", [
     ("C", "VG ", 799, 1985, "Mall purchase. Discreet bag required."),
   ]),
   ("True Blue", 1986, "Sire", "Pop", [
     ("L", "VG+", 999, 1986, "Papa Don't Preach on loop"),
   ]),
 ]),
 ("Talking Heads", "USA", 3, [
   ("Remain in Light", 1980, "Sire", "New Wave", [
     ("L", "VG+", 899, 1981, "Once in a lifetime. Twice, actually."),
   ]),
   ("Speaking in Tongues", 1983, "Sire", "New Wave", [
     ("L", "NM ", 999, 1983, "Fancy packaging. Cover is the star."),
   ]),
 ]),
 ("The Smiths", "UK", 5, [
   ("Meat Is Murder", 1985, "Rough Trade", "Indie", [
     ("L", "VG ", 899, 1986, "Argued about it in the cafeteria"),
   ]),
   ("The Queen Is Dead", 1986, "Rough Trade", "Indie", [
     ("L", "VG+", 999, 1986, "Quietly devastating"),
     ("C", "VG ", 799, 1987, "Bedroom soundtrack. Curtains drawn."),
   ]),
 ]),
 ("New Order", "UK", 3, [
   ("Power, Corruption & Lies", 1983, "Factory", "Synthpop", [
     ("L", "VG+", 999, 1984, "Blue Monday is on a different single"),
   ]),
   ("Low-Life", 1985, "Factory", "Synthpop", [
     ("C", "VG ", 799, 1986, "Perfect Kiss. Perfect tape."),
   ]),
 ]),
 ("Kate Bush", "UK", 8, [
   ("The Dreaming", 1982, "EMI", "Art Pop", [
     ("L", "VG ", 899, 1983, "Baffling. Brilliant. Baffling."),
   ]),
   ("Hounds of Love", 1985, "EMI", "Art Pop", [
     ("L", "NM ", 999, 1985, "Side B is a concept. Worth the flip."),
     ("C", "VG+", 799, 1986, "Running Up That Hill, in the car"),
   ]),
 ]),
 ("U2", "Ireland", 6, [
   ("War", 1983, "Island", "Rock", [
     ("L", "VG ", 899, 1983, "Sunday Bloody Sunday, loud"),
   ]),
   ("The Joshua Tree", 1987, "Island", "Rock", [
     ("L", "VG+", 1099, 1987, "Second copy lives in a tree. Joking."),
     ("C", "G  ", 799, 1987, "Road trip. Hit the rewind a lot."),
   ]),
 ]),
 ("Bruce Springsteen", "USA", 4, [
   ("Born in the U.S.A.", 1984, "Columbia", "Rock", [
     ("L", "VG ", 899, 1984, "Not a patriotic song. Look it up."),
     ("C", "VG ", 799, 1985, "Truck tape"),
   ]),
 ]),
 ("Cyndi Lauper", "USA", 10, [
   ("She's So Unusual", 1983, "Portrait", "Pop", [
     ("L", "VG+", 899, 1984, "Girls just wanna. Boys too, apparently."),
   ]),
 ]),
 ("Tears for Fears", "UK", 8, [
   ("Songs from the Big Chair", 1985, "Mercury", "Synthpop", [
     ("L", "VG+", 999, 1985, "Everybody wants to rule the world"),
     ("C", "VG ", 799, 1986, "Shout. Shout. Let it all out."),
   ]),
 ]),
 ("Eurythmics", "UK", 5, [
   ("Sweet Dreams (Are Made of This)", 1983, "RCA", "Synthpop", [
     ("L", "VG ", 899, 1983, "Annie's orange crop = the real star"),
   ]),
 ]),
 ("Culture Club", "UK", 9, [
   ("Colour by Numbers", 1983, "Virgin", "New Romantic", [
     ("C", "VG ", 799, 1984, "Karma chameleon. Wore the hat."),
   ]),
 ]),
 ("The Human League", "UK", 10, [
   ("Dare", 1981, "Virgin", "Synthpop", [
     ("L", "VG+", 899, 1982, "That asymmetric haircut. Magnificent."),
     ("S", "VG ", 599, 1982, "Don't You Want Me, 12in"),
   ]),
 ]),
 ("Soft Cell", "UK", 6, [
   ("Non-Stop Erotic Cabaret", 1981, "Some Bizzare", "Synthpop", [
     ("L", "VG ", 999, 1982, "Tainted Love, extended, twice"),
   ]),
 ]),
 ("A-ha", "Norway", 9, [
   ("Hunting High and Low", 1985, "Warner Bros.", "Synthpop", [
     ("C", "VG+", 799, 1986, "Take On Me, rotoscope in my head"),
   ]),
 ]),
 ("Wham!", "UK", 10, [
   ("Make It Big", 1984, "Epic", "Pop", [
     ("L", "VG ", 899, 1985, "Wake me up before you go-go. Please."),
   ]),
 ]),
 ("Pet Shop Boys", "UK", 4, [
   ("Please", 1986, "Parlophone", "Synthpop", [
     ("L", "NM ", 999, 1986, "West End Girls. Deadpan perfection."),
   ]),
 ]),
 ("The Police", "UK", 6, [
   ("Synchronicity", 1983, "A&M", "Rock", [
     ("L", "VG ", 899, 1983, "Every Breath You Take. Creepy, great."),
     ("C", "VG ", 799, 1984, "Beach tape. Sand still inside."),
   ]),
 ]),
 ("Guns N' Roses", "USA", 10, [
   ("Appetite for Destruction", 1987, "Geffen", "Hard Rock", [
     ("L", "VG ", 999, 1988, "Original cover (the censored one's lame)"),
     ("C", "G  ", 799, 1988, "Parental advisory: mom found it"),
   ]),
 ]),
 ("Def Leppard", "UK", 10, [
   ("Pyromania", 1983, "Mercury", "Hard Rock", [
     ("L", "VG+", 899, 1983, "Photograph, on repeat, for months"),
   ]),
 ]),
 ("Whitney Houston", "USA", 7, [
   ("Whitney Houston", 1985, "Arista", "Pop", [
     ("C", "VG+", 799, 1986, "How Will I Know. Now I know."),
   ]),
 ]),
 ("Run-D.M.C.", "USA", 2, [
   ("Raising Hell", 1986, "Profile", "Hip Hop", [
     ("L", "VG ", 899, 1986, "Walk This Way. With Aerosmith. Obviously"),
   ]),
 ]),
 ("Beastie Boys", "USA", 4, [
   ("Licensed to Ill", 1986, "Def Jam", "Hip Hop", [
     ("C", "G  ", 799, 1987, "Fight for your right to dub it"),
   ]),
 ]),
 ("Joy Division", "UK", 2, [
   ("Closer", 1980, "Factory", "Post-Punk", [
     ("L", "VG ", 999, 1984, "Found late. Cried a bit. Fine."),
   ]),
 ]),
 ("R.E.M.", "USA", 3, [
   ("Murmur", 1983, "I.R.S.", "Alternative", [
     ("L", "VG+", 899, 1984, "Lyrics unknown. Vibes immaculate."),
   ]),
 ]),
 ("The Clash", "UK", 4, [
   ("Combat Rock", 1982, "CBS", "Punk", [
     ("L", "VG ", 899, 1982, "Should I stay or should I go? Stayed."),
   ]),
 ]),
 ("Phil Collins", "UK", 1, [
   ("No Jacket Required", 1985, "Atlantic", "Pop", [
     ("C", "VG ", 799, 1985, "Nice tape. Don't tell anyone."),
   ]),
 ]),

 # ---- The True North strong and free ----------------------------------
 ("Rush", "Canada", 7, [
   ("Moving Pictures", 1981, "Anthem", "Prog Rock", [
     ("L", "VG+", 899, 1982, "Tom Sawyer in the basement. Geddy!"),
   ]),
   ("Signals", 1982, "Anthem", "Prog Rock", [
     ("C", "VG ", 799, 1983, "New World Man. Willowdale pride."),
   ]),
   ("Grace Under Pressure", 1984, "Anthem", "Prog Rock", [
     ("L", "NM ", 999, 1984, "Red Sector A. Very Cold War, eh."),
   ]),
 ]),
 ("Bryan Adams", "Canada", 5, [
   ("Cuts Like a Knife", 1983, "A&M", "Rock", [
     ("C", "VG ", 799, 1984, "Straight from the heart, via Vancouver"),
   ]),
   ("Reckless", 1984, "A&M", "Rock", [
     ("L", "VG+", 899, 1985, "Best summer of my life. Mostly '85."),
     ("C", "G  ", 799, 1985, "School bus tape. Wore it thin."),
   ]),
 ]),
 ("Neil Young", "Canada", 3, [
   ("Trans", 1982, "Geffen", "Experimental", [
     ("L", "VG ", 899, 1983, "Vocoder. Confused the whole concert."),
   ]),
   ("Freedom", 1989, "Reprise", "Rock", [
     ("C", "VG+", 899, 1989, "Rockin' in the Free World. Loud."),
   ]),
 ]),
 ("Leonard Cohen", "Canada", 1, [
   ("Various Positions", 1984, "Passport", "Folk", [
     ("L", "VG+", 899, 1985, "Hallelujah. Little did we know."),
   ]),
   ("I'm Your Man", 1988, "Columbia", "Art Pop", [
     ("C", "VG ", 799, 1989, "First We Take Manhattan. Gravel and hat."),
   ]),
 ]),
 ("Joni Mitchell", "Canada", 4, [
   ("Wild Things Run Fast", 1982, "Geffen", "Pop", [
     ("L", "VG ", 899, 1983, "Prairie girl, big city voice."),
   ]),
 ]),
 ("Anne Murray", "Canada", 5, [
   ("A Little Good News", 1983, "Capitol", "Country Pop", [
     ("L", "VG ", 899, 1983, "Mom's copy. Mom's rules."),
   ]),
 ]),
 ("k.d. lang", "Canada", 3, [
   ("Angel with a Lariat", 1987, "Sire", "Country", [
     ("C", "VG ", 799, 1988, "Consort, Alberta's finest. Fight me."),
   ]),
 ]),
 ("Corey Hart", "Canada", 6, [
   ("First Offense", 1983, "Aquarius", "Pop Rock", [
     ("C", "VG ", 799, 1984, "Sunglasses at Night. Wore them. Indoors."),
   ]),
 ]),
 ("Honeymoon Suite", "Canada", 9, [
   ("The Big Prize", 1985, "Warner Bros.", "Hard Rock", [
     ("L", "VG ", 899, 1986, "New Girl Now. Niagara Falls anthem."),
   ]),
 ]),
 ("Platinum Blonde", "Canada", 10, [
   ("Standing in the Dark", 1983, "CBS", "New Wave", [
     ("L", "VG+", 899, 1984, "Not platinum. Very, very blonde."),
   ]),
 ]),
 ("Loverboy", "Canada", 8, [
   ("Get Lucky", 1981, "Columbia", "Rock", [
     ("L", "VG ", 899, 1982, "Working for the weekend. Calgary-style."),
   ]),
 ]),
 ("Glass Tiger", "Canada", 8, [
   ("The Thin Red Line", 1986, "Capitol", "Pop Rock", [
     ("C", "VG ", 799, 1986, "Don't Forget Me. We didn't."),
   ]),
 ]),
 ("The Tragically Hip", "Canada", 4, [
   ("Up to Here", 1989, "MCA", "Rock", [
     ("C", "VG+", 799, 1989, "Blow at High Dough. Kingston forever."),
   ]),
 ]),
 ("Blue Rodeo", "Canada", 4, [
   ("Outskirts", 1987, "WEA", "Country Rock", [
     ("L", "VG+", 899, 1988, "Try. Cried at the cottage."),
   ]),
 ]),
 ("Triumph", "Canada", 8, [
   ("Allied Forces", 1981, "RCA", "Hard Rock", [
     ("L", "VG ", 899, 1982, "Magic Power. Air-guitar certified."),
   ]),
 ]),
 ("Kim Mitchell", "Canada", 7, [
   ("Akimbo Alogo", 1984, "Anthem", "Rock", [
     ("C", "VG ", 799, 1985, "Go for a Soda. Cottage-country classic."),
   ]),
 ]),
 ("Cowboy Junkies", "Canada", 2, [
   ("The Trinity Session", 1988, "RCA", "Alt Country", [
     ("C", "NM ", 899, 1989, "One church, one mic. Sweet Jane."),
   ]),
 ]),
 ("Men Without Hats", "Canada", 6, [
   ("Rhythm of Youth", 1982, "Statik", "Synthpop", [
     ("L", "VG ", 899, 1983, "The Safety Dance. Yes, we danced."),
     ("S", "VG ", 599, 1983, "Safety Dance 12in. Extra hand-waving."),
   ]),
 ]),
 ("Martha and the Muffins", "Canada", 5, [
   ("Metro Music", 1980, "Dindisc", "New Wave", [
     ("L", "VG ", 899, 1981, "Echo Beach. Far away in time."),
   ]),
 ]),
 ("Spoons", "Canada", 6, [
   ("Arias & Symphonies", 1982, "Ready", "New Wave", [
     ("L", "VG ", 899, 1983, "Nova Heart. Burlington, represent."),
   ]),
 ]),
 ("Parachute Club", "Canada", 9, [
   ("Parachute Club", 1983, "Current", "Dance Pop", [
     ("L", "VG ", 899, 1984, "Rise Up. Toronto, 1983."),
   ]),
 ]),
 ("Alannah Myles", "Canada", 9, [
   ("Alannah Myles", 1989, "Atlantic", "Rock", [
     ("C", "VG ", 799, 1989, "Black Velvet. Elvis is in the room."),
   ]),
 ]),
]


# ---------------------------------------------------------------------------
# The real box.  Cassettes transcribed from a photo of the actual collection.
# Condition, price and year bought are unknown (0 / "?"); the program shows
# "Grade unknown", "priceless" and "????".  Album years are only filled in
# where known with confidence (0 = unknown).  Entries for an artist or album
# that already exists above are merged by gen_sql.py.
# ---------------------------------------------------------------------------
def real(note="From the real box. Priceless.", media="C"):
    return (media, "?", 0, 0, note)


CCM = "From the real box. CCM forever."

DATA += [
 ("Glad", "USA", 3, [
   ("The Acapella Project", 1987, "Benson", "CCM", [real(CCM)]),
 ]),
 ("Petra", "USA", 8, [
   ("War and Remembrance", 1986, "Star Song", "CCM",
    [real(CCM), real("Second copy. Petra insurance.")]),
   ("Beyond Belief", 1990, "Star Song", "CCM", [real(CCM)]),
 ]),
 ("Rich Mullins", "USA", 5, [
   ("Winds of Heaven... Stuff of Earth", 1988, "Reunion", "CCM", [real(CCM)]),
   ("Never Picture Perfect", 1989, "Reunion", "CCM", [real(CCM)]),
   ("The World as Best as I Remember It", 1991, "Reunion", "CCM", [real(CCM)]),
   ("A Liturgy, a Legacy & a Ragamuffin Band", 1993, "Reunion", "CCM", [real(CCM)]),
 ]),
 ("dc Talk", "USA", 7, [
   ("Jesus Freak", 1995, "ForeFront", "CCM", [real(CCM)]),
 ]),
 ("The Imperials", "USA", 6, [
   ("Stand by the Power", 1982, "DaySpring", "CCM", [real(CCM)]),
 ]),
 ("Amy Grant", "USA", 8, [
   ("My Father's Eyes", 1979, "Myrrh", "CCM", [real(CCM)]),
   ("Lead Me On", 1988, "Myrrh", "CCM", [real(CCM)]),
 ]),
 ("Sandi Patty", "USA", 7, [
   ("Hymns Just for You", 0, "?", "CCM", [real(CCM)]),
 ]),
 ("Vangelis", "Greece", 5, [
   ("Portraits (So Long Ago, So Clear)", 1981, "RCA", "Electronic", [real()]),
 ]),
 ("Bruce Cockburn", "Canada", 4, [
   ("High Winds, White Sky", 1971, "True North", "Folk", [real()]),
   ("Circles in the Stream", 1977, "True North", "Folk", [real()]),
 ]),
 ("Gloria Estefan", "USA", 8, [
   ("Mi Tierra", 1993, "Epic", "Latin Pop", [real()]),
 ]),
 ("Phil Keaggy", "USA", 5, [
   ("Beyond Nature", 1981, "Sparrow", "CCM", [real(CCM)]),
   ("Town to Town", 1983, "Sparrow", "CCM", [real(CCM)]),
 ]),
 ("Billy Joel", "USA", 4, [
   ("Greatest Hits Volume I & II", 1985, "Columbia", "Rock", [real()]),
 ]),
 ("Seal", "UK", 1, [
   ("Seal", 0, "?", "Soul", [real()]),
 ]),
 ("Chicago", "USA", 5, [
   ("Chicago 17", 1984, "Warner Bros.", "Rock", [real()]),
 ]),
 ("John Williams", "USA", 2, [
   ("Star Wars (Original Soundtrack)", 1977, "20th Century", "Soundtrack", [real()]),
   ("Return of the Jedi (Soundtrack)", 1983, "RSO", "Soundtrack", [real()]),
 ]),
 ("Yello", "Switzerland", 3, [
   ("Zebra", 1994, "Mercury", "Electronic", [real()]),
 ]),
 ("Gowan", "Canada", 6, [
   ("Strange Animal", 1985, "Columbia", "Rock", [real("From the real box. Not that strange, eh.")]),
 ]),
 ("Sting", "UK", 4, [
   ("The Dream of the Blue Turtles", 1985, "A&M", "Pop", [real()]),
   ("...Nothing Like the Sun", 1987, "A&M", "Pop", [real()]),
 ]),
 ("Malcolm McLaren", "UK", 8, [
   ("Fans", 1984, "Virgin", "Opera Pop", [real("Won as 10th caller on the request line")]),
 ]),
 ("David Foster", "Canada", 3, [
   ("The Symphony Sessions", 1988, "Atlantic", "Instrumental", [real()]),
 ]),
 ("Hall & Oates", "USA", 9, [
   ("Big Bam Boom", 1984, "RCA", "Pop", [real()]),
 ]),
 ("Level 42", "UK", 7, [
   ("World Machine", 1985, "Polydor", "Jazz Funk", [real()]),
 ]),
 ("Howard Jones", "UK", 10, [
   ("The Best of Howard Jones", 1993, "Elektra", "Synthpop", [real()]),
 ]),
 ("Queen", "UK", 9, [
   ("Greatest Hits", 1981, "EMI", "Rock", [real()]),
 ]),
 ("Dmitri Shostakovich", "USSR", 2, [
   ("Symphony No. 5", 0, "?", "Classical", [real("From the real box. Made in Canada.")]),
 ]),
 ("Gustav Mahler", "Austria", 3, [
   ("Symphony No. 5", 0, "?", "Classical", [real()]),
 ]),
 ("Yes", "UK", 8, [
   ("90125", 1983, "Atco", "Prog Rock", [real()]),
 ]),
 ("Elvis Presley", "USA", 10, [
   ("Elvis' Gold Records", 0, "RCA", "Rock and Roll", [real("From the real box. The King.")]),
 ]),
 ("Various Artists", "Various", 0, [
   ("Beverly Hills Cop (Soundtrack)", 1984, "MCA", "Soundtrack", [real()]),
   ("Jesus Christ Superstar (Soundtrack)", 1973, "MCA", "Soundtrack", [real("From the real box. Twin-pack tape.")]),
   ("Les Miserables (Broadway Album)", 1987, "Geffen", "Musical", [real()]),
   ("Personal Worship 2", 0, "RPI", "Worship", [real(CCM)]),
 ]),
 ("Trooper", "Canada", 8, [
   ("Hot Shots", 1979, "MCA", "Rock", [real("From the real box. Raise a Little Hell.")]),
 ]),
 ("Michael W. Smith", "USA", 7, [
   ("The Big Picture", 1986, "Reunion", "CCM", [real(CCM)]),
 ]),
 ("The Praise Band", "USA", 3, [
   ("You Are So Faithful", 0, "Maranatha! Music", "Worship", [real(CCM)]),
   ("Jesus, Mighty God", 0, "Maranatha! Music", "Worship", [real(CCM)]),
   ("Everlasting (Praise Band 3)", 0, "Maranatha! Music", "Worship", [real(CCM)]),
 ]),
 ("Langley Vineyard", "Canada", 3, [
   ("Changed by Your Glory", 0, "?", "Worship", [real(CCM)]),
 ]),
 ("The Archers", "USA", 5, [
   ("At Their Very Best", 0, "Light", "CCM", [real(CCM)]),
 ]),
 ("Carman", "USA", 6, [
   ("Addicted to Jesus", 1988, "Benson", "CCM", [real(CCM)]),
 ]),
 ("Don Moen", "USA", 4, [
   ("Worship with Don Moen", 0, "Hosanna! Music", "Worship", [real(CCM)]),
 ]),
 ("Warren Halstrom", "USA", 3, [
   ("Friends Thru the Fire", 0, "Image 7", "CCM", [real(CCM)]),
 ]),
 ("John Michael Talbot", "USA", 2, [
   ("The Regathering", 1987, "Sparrow", "CCM", [real(CCM)]),
 ]),
 ("Glen Garrett", "USA", 3, [
   ("It Is Written", 0, "Greentree", "CCM", [real(CCM)]),
 ]),
 ("Johnny Markin", "USA", 3, [
   ("The Call Home", 0, "?", "CCM", [real(CCM)]),
 ]),
 ("Mickey & Becki Moore", "USA", 3, [
   ("Love Song for Number 2", 0, "Image 7", "CCM", [real(CCM)]),
 ]),
 ("The Plankerdown Band", "USA", 3, [
   ("The Jig Is Up", 0, "?", "Folk", [real()]),
 ]),
 ("White Heart", "USA", 7, [
   ("Highlands", 0, "Sparrow", "CCM", [real(CCM)]),
   ("Tales of Wonder", 0, "Sparrow", "CCM", [real(CCM)]),
   ("Power House", 0, "Sparrow", "CCM", [real(CCM)]),
 ]),
 ("Ennio Morricone", "Italy", 3, [
   ("The Mission (Soundtrack)", 1986, "Virgin", "Soundtrack", [real()]),
 ]),
 ("Thompson Twins", "UK", 9, [
   ("Into the Gap", 1984, "Arista", "Synthpop", [real()]),
 ]),
 ("Ian Thomas", "Canada", 5, [
   ("Levity", 0, "?", "Rock", [real("From the real box. Canadian dad-rock.")]),
 ]),
 ("Nik Kershaw", "UK", 9, [
   ("Radio Musicola", 1986, "MCA", "Pop", [real()]),
 ]),
 ("Walk on Water", "USA", 5, [
   ("Walk on Water", 0, "Alarma", "CCM", [real(CCM)]),
 ]),
 ("Paul Janz", "?", 5, [
   ("Trust", 0, "?", "CCM", [real(CCM)]),
 ]),
 ("Rob Frazier", "USA", 5, [
   ("Retrospect", 0, "?", "CCM", [real(CCM)]),
 ]),
 ("Stanley Fisher, Ph.D.", "USA", 1, [
   ("Discovering the Power of Self-Hypnosis", 0, "?", "Self-Help", [real("Real box. You are getting sleepy.")]),
 ]),
 ("Stephen R. Covey", "USA", 1, [
   ("Getting the Most Out of Your 7 Habits", 0, "?", "Self-Help", [real("From the real box. Be proactive!")]),
 ]),

 # --- more copies/albums for artists already on the shelf ---------------
 ("Honeymoon Suite", "Canada", 9, [
   ("The Big Prize", 1985, "Warner Bros.", "Hard Rock", [real("The tape. The LP is a separate story.")]),
 ]),
 ("Kim Mitchell", "Canada", 7, [
   ("Rockland", 1989, "Alert", "Rock", [real()]),
 ]),
 ("Phil Collins", "UK", 1, [
   ("...But Seriously", 1989, "Atlantic", "Pop", [real()]),
 ]),
 ("The Police", "UK", 6, [
   ("Zenyatta Mondatta", 1980, "A&M", "Rock", [real()]),
   ("Every Breath You Take: The Singles", 1986, "A&M", "Rock", [real()]),
 ]),
 ("The Human League", "UK", 10, [
   ("Dare", 1981, "Virgin", "Synthpop", [real("The tape copy of Dare. Obviously.")]),
   ("Fascination!", 1983, "Virgin", "Synthpop", [real()]),
   ("Crash", 1986, "Virgin", "Synthpop", [real()]),
 ]),
]
