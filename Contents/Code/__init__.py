import re
from datetime import datetime

LoggedIn = SharedCodeService.tv4play.LoggedIn
Login    = SharedCodeService.tv4play.Login

TITLE  = 'TV4 Play'
PREFIX = '/video/tv4play'

BASE_URL = 'http://www.tv4play.se'

RE_VIDEO_ID = '(?<=video_id=)[0-9]+'

HTTP_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_5) AppleWebKit/536.26.17 (KHTML, like Gecko) Version/6.0.2 Safari/536.26.17"

API_BASE_URL   = 'http://webapi.tv4play.se'
CATEGORIES_URL = API_BASE_URL + '/play/categories'
MOVIES_URL     = API_BASE_URL + '/play/movie_assets?platform=web&start=%s&rows=%s'

TEMPLATE_VIDEO_URL = 'http://www.tv4play.se/%s/%s?video_id=%s'

ITEMS_PER_PAGE = 50

DISCLAIMER_NOTE = unicode("Vissa program är skyddade med DRM(Digital Rights Management). Dessa kan för närvarande ej spelas upp.")
PREMIUM_PREVIEW_NOTE = unicode("Notera att du ej kan spela upp de program som endast är tillgängliga för Premium.")

NO_PROGRAMS_FOUND_HEADER  = "Inga program funna"
NO_PROGRAMS_FOUND_MESSAGE = unicode("Kunde inte hitta några program. ") + DISCLAIMER_NOTE
SERVER_MESSAGE            = unicode("Kunde ej få kontakt med TV4 servern")

DAYS = [
    unicode("Måndag"),
    unicode("Tisdag"),
    unicode("Onsdag"),
    unicode("Torsdag"),
    unicode("Fredag"),
    unicode("Lördag"),
    unicode("Söndag")
]


####################################################################################################
def Start():
    # Set the default ObjectContainer attributes
    ObjectContainer.title1 = TITLE
    
    # Set the default cache time
    HTTP.CacheTime             = 300
    HTTP.Headers['User-agent'] = HTTP_USER_AGENT

    # Try to login
    Login()

###################################################################################################
def ValidatePrefs():
    oc         = ObjectContainer(title2 = unicode("Inställningar"))
    oc.header  = ""
    oc.message = ""
    
    if Prefs['premium'] and Prefs['email'] and Prefs['password']:
        if Login():
            oc.header = "Inloggad"
            oc.message = unicode("Du är nu inloggad")
        else:
            oc.header = "Inloggningen misslyckades"
            oc.message = unicode("Felaktigt användarnamn eller lösenord?")
            return oc
            
    elif Prefs['premium']:
        oc.header = "Information saknas"
        oc.message = unicode("Användarnamn och/eller lösenord saknas.")
        return oc

    elif not Prefs['onlyfree']:
        oc.header = unicode("Alla program")
        oc.message = PREMIUM_PREVIEW_NOTE
    else:
        oc.header = "Gratis"
        oc.message = unicode("Visar endast program som är gratis.")
         
    oc.message = oc.message + ' ' + DISCLAIMER_NOTE + unicode(" Starta om för att inställningarna skall börja gälla.")
    
    return oc

####################################################################################################
@handler(PREFIX, TITLE)
def MainMenu():
    oc = ObjectContainer(no_cache = True)

    title = 'Mest sedda programmen'
    oc.add(
        DirectoryObject(
            key = Callback(TV4MostWatched, title = title),
            title = title
        )
    )
    
    title = 'Senaste veckans TV'
    oc.add(
        DirectoryObject(
            key = Callback(TV4Catchup, title = title),
            title = title
        )
    )

    title = unicode('Livesändningar')
    oc.add(
        DirectoryObject(
            key = Callback(TV4Live, title = title),
            title = title
        )
    )

    title = 'Kategorier'
    oc.add(
        DirectoryObject(
            key = Callback(TV4Categories, title = title),
            title = title
        )
    )
        
    title = 'Alla program'
    oc.add(
        DirectoryObject(
            key = Callback(TV4Shows, title = title), 
            title = title
        )
    )

    oc.add(
        PrefsObject(
            title = unicode('Inställningar'),
            summary = unicode('Logga in för att använda Premium\r\n\r\nDu kan även välja att visa alla program för att se vad Premium innebär.\r\n\r\n' + DISCLAIMER_NOTE)
        )
    )

    title = unicode('Sök')
    oc.add(
        InputDirectoryObject(
            key = Callback(Search, title = title),
            title  = title,
            prompt = title
        )
    )

    return oc

###################################################################################################
@route(PREFIX + '/TV4MostWatched', episodes = bool)
def TV4MostWatched(title, episodes = True):
    oc = ObjectContainer(title2 = unicode(title))

    if episodes:
        oc.add(DirectoryObject(key   = Callback(TV4MostWatched, 
                                                title      = title + " - Klipp",
                                                episodes   = False, 
                                                ),
                               title = "Klipp"
                               )
               )
    
    videos = JSON.ObjectFromURL(GetMostWatchedURL(episodes = episodes))
    oc = Videos(oc, videos)
    
    if len(oc) < 1:
        oc.header  = NO_PROGRAMS_FOUND_HEADER
        oc.message = NO_PROGRAMS_FOUND_MESSAGE
        
    return oc
    
####################################################################################################
@route(PREFIX + '/TV4Catchup')
def TV4Catchup(title):
    oc = ObjectContainer(title2 = unicode(title))

    now = datetime.today()  #TODO Can't find a framework function for this?
    for i in range (0, 7):
        date = now - Datetime.Delta(days = i)
        
        if i == 0:
            title = unicode('Idag')
        elif i == 1:
            title = unicode('Igår')
        else:
            title = DAYS[date.weekday()]
        
        month = str(date.month)
        if len(month) <= 1:
            month = '0' + month
            
        day = str(date.day)
        if len(day) <= 1:
            day = '0' + day
            
        url = GetListingsURL('%s%s%s' % (date.year, month, day))
        dateString = '%s-%s-%s' % (date.year, month, day)
        
        oc.add(
            DirectoryObject(
                key = Callback(TV4ListingVideos, url = url, title = dateString),
                title = title
            )
        )
    
    return oc 

####################################################################################################
@route(PREFIX + '/TV4ListingVideos')
def TV4ListingVideos(url, title):
    oc = ObjectContainer(title2 = unicode(title))
    
    videos = JSON.ObjectFromURL(url)

    if not videos['channels']:
        oc.header  = NO_PROGRAMS_FOUND_HEADER
        oc.message = SERVER_MESSAGE
        
        return oc
    
    vman_ids = ''
    for video in videos['channels']['TV4']['entries']:
        if 'vman_id' in video:
            vman_ids = vman_ids + str(video['vman_id']) + '%2C'
            
    videos = JSON.ObjectFromURL(GetVideosURL(vman_ids))
    oc = Videos(oc, videos)
        
    if len(oc) < 1:
        oc.header  = NO_PROGRAMS_FOUND_HEADER
        oc.message = NO_PROGRAMS_FOUND_MESSAGE

    return oc

####################################################################################################
@route(PREFIX + '/TV4Live')
def TV4Live(title):
    oc = ObjectContainer(title2 = unicode(title))
    
    t = datetime.today()
    today = "%04i%02i%02i" % (t.year, t.month, t.day)
    t = t + Datetime.Delta(days = 2)
    too_late = "%04i%02i%02i" % (t.year, t.month, t.day)

    # Only interested in broadcasts today and tomorrow
    videos = JSON.ObjectFromURL(GetLiveURL(today, too_late), cacheTime = 0)
    oc = Videos(oc, videos, (today,too_late))
    
    if len(oc) < 1:
        oc.header  = NO_PROGRAMS_FOUND_HEADER
        oc.message = unicode('Inga livesändningar tillgängliga för tillfället')

    return oc

####################################################################################################
@route(PREFIX + '/TV4Categories')
def TV4Categories(title):
    oc = ObjectContainer(title2 = unicode(title))

    categories = JSON.ObjectFromURL(CATEGORIES_URL)

    for category in categories:
        oc.add(
            DirectoryObject(
                key = Callback(TV4Shows, title = category["name"], categoryId = unicode(category["nid"])),
                title = unicode(category["name"])
            )
        )

    if Prefs['premium'] or not Prefs['onlyfree']:
        title = 'Filmer'
        oc.add(
            DirectoryObject(
                key = Callback(TV4Movies, title = title),
                title = title
            )
        )

    oc.objects.sort(key=lambda obj: obj.title)
    
    return oc

####################################################################################################
@route(PREFIX + '/TV4Shows', query = list, page = int)
def TV4Shows(title, categoryId = '', query = '', page = 1):
    oc = ObjectContainer(title2 = unicode(title))
    
    programs = JSON.ObjectFromURL(GetProgramsURL(page, categoryId, query))
    oc = Programs(oc, programs)

    if len(oc) < 1:
        oc.header  = NO_PROGRAMS_FOUND_HEADER
        oc.message = SERVER_MESSAGE
        
        return oc
    else:
        # Offset starts at 0 - page at 1...
        (previousItem, nextItem) = GetNavigationItems((page-1)*ITEMS_PER_PAGE, programs['total_hits'])

        if previousItem:
            (previousOffset, previousTitle, previousSummary) = previousItem
            # Prepend PreviousItem directory
            oc.objects.reverse()
            oc.add(DirectoryObject(
                    key     = Callback(TV4Shows,
                                       title      = title,
                                       categoryId = categoryId,
                                       query      = query,
                                       page       = (previousOffset/ITEMS_PER_PAGE)+1
                                       ),
                    title   = previousTitle,
                    summary = previousSummary
                    )
                   )
            oc.objects.reverse()

        if nextItem:
            (nextOffset, nextTitle, nextSummary) = nextItem
            # Append NextItem directory
            oc.add(NextPageObject(
                    key     = Callback(TV4Shows,
                                       title      = title,
                                       categoryId = categoryId,
                                       query      = query,
                                       page       = (nextOffset/ITEMS_PER_PAGE)+1
                                       ),
                    title   = nextTitle,
                    summary = nextSummary
                    )
                   )
        
    return oc
    
####################################################################################################
@route(PREFIX + '/TV4ShowChoice')
def TV4ShowChoice(title, showId, art, thumb, summary):
    title = unicode(title)
    oc = ObjectContainer(title2 = title)
    showId = String.Quote(showId)
    
    episodes = JSON.ObjectFromURL(GetShowVideosURL(episodes = True, id = showId))
    clips    = JSON.ObjectFromURL(GetShowVideosURL(episodes = False, id = showId))

    if episodes['total_hits'] > 0 and clips['total_hits'] > 0:
        oc.add(
            DirectoryObject(
                key =
                    Callback(
                        TV4ShowVideos, 
                        title = title, 
                        showId = showId, 
                        art = art,
                        episodeReq = False
                    ),
                title = "Klipp",
                thumb = thumb,
                summary = unicode(summary),
                art = art
            )
        )
        episodeReq = True
    elif episodes['total_hits'] > 0 or clips['total_hits'] > 0:
        if clips['total_hits'] > 0:
            title = title + " - Klipp"

        episodeReq = episodes['total_hits'] > 0

    if episodes['total_hits'] + clips['total_hits'] > 0:
        episode_oc = TV4ShowVideos(title      = title,
                                   showId     = showId,
                                   art        = art,
                                   episodeReq = episodeReq
                                   )

        for object in episode_oc.objects:
            oc.add(object)

    if len(oc) < 1:  
        oc.header  = NO_PROGRAMS_FOUND_HEADER
        oc.message = NO_PROGRAMS_FOUND_MESSAGE

    return oc

####################################################################################################
@route(PREFIX + '/TV4ShowVideos', episodeReq = bool, query = list, page = int)
def TV4ShowVideos(title, showId, art, episodeReq, query = '', page = 1):
    oc = ObjectContainer(title2 = unicode(title))
    
    videos = JSON.ObjectFromURL(GetShowVideosURL(episodes = episodeReq, id = showId, query = query, page = page))
    oc = Videos(oc, videos, strip_show = True)

    try:
        sortOnAirData(oc)
    except:
        oc.objects.reverse()
    
    if len(oc) < 1:
        oc.header  = NO_PROGRAMS_FOUND_HEADER
        
        if page == 1:
            oc.message = NO_PROGRAMS_FOUND_MESSAGE
        else:
            oc.message = unicode('Inga fler program funna')

    if len(oc) > 0 or page != 1:
        oc = AddTV4ShowVideosNavigationDirs(oc,
                                            page, 
                                            videos['total_hits'],
                                            title,
                                            showId,
                                            art,
                                            episodeReq,
                                            query
                                            )
    return oc

####################################################################################################
@route(PREFIX + '/TV4PremiumRequired')
def TV4PremiumRequired():
    oc         = ObjectContainer()
    oc.header  = unicode("Premium krävs")
    oc.message = unicode("För att spela upp detta program krävs ett Premium abonnemang.\r\nwww.tv4play.se/premium")
    
    return oc

####################################################################################################
@route(PREFIX + '/TV4Movies', offset = int)
def TV4Movies(title, offset = 0):
    oc = ObjectContainer(title2 = unicode(title))

    while len(oc) < ITEMS_PER_PAGE:
        x = 0
        movies = JSON.ObjectFromURL(MOVIES_URL % (offset, ITEMS_PER_PAGE))
        for movie in movies['results']:
            x = x+1
            if 'is_drm_protected' in movie and movie['is_drm_protected']:
                continue

            try:
                genres = [movie['genre']] if movie['genre'] else []
            except:
                genres = []

            try:
                for sub in movie['sub_genres']:
                    genres.append(sub)
            except:
                pass

            try:
                duration = int(movie['length']) * 60 * 1000
            except:
                duration = None
            
            try:
                year = int(movie['production_year'])
            except:
                year = None

            try:
                directors = [movie['director']] if movie['director'] else []
            except:
                directors = []

            try:
                art = movie['image']
            except:
                art = None
            
            try:
                thumb = movie['poster_image']
                if not thumb.startswith('http'):
                    thumb = API_BASE_URL + '/play' + thumb
            except:
                thumb = None
            
            summary = movie['synopsis']
            if not summary:
                summary = movie['description_short']

            if not Prefs['premium']:
                oc.add(
                    DirectoryObject(
                        key = Callback(TV4PremiumRequired),
                        title = movie['title'],
                        summary = summary,
                        duration = duration,
                        thumb = thumb,
                        art = art
                        )
                    )
            else:
                oc.add(
                    MovieObject(
                        url = TEMPLATE_VIDEO_URL % ('film', movie['id'], movie['id']),
                        title = movie['title'],
                        genres = genres,
                        summary = summary,
                        duration = duration,
                        original_title = movie['original_title'],
                        year = year,
                        directors = directors,
                        thumb = thumb,
                        art = art
                        )
                    )
            if len(oc) >= ITEMS_PER_PAGE:
                # Modify offset since maybe we're not done with this page
                offset = offset+x-ITEMS_PER_PAGE
                break
        if len(movies['results']) == 0:
            break
        if len(oc) < ITEMS_PER_PAGE:
            offset = offset+ITEMS_PER_PAGE

    # Ignore previous since drm_protection messes up previous page offset
    (previousItem, nextItem) = GetNavigationItems(offset, movies['total_hits'])

    if nextItem and len(movies['results']) > 0:
        (nextOffset, nextTitle, nextSummary) = nextItem
        # Append NextItem directory
        oc.add(
            NextPageObject(
                key    = Callback(TV4Movies, title  = title, offset = nextOffset),
                title  = nextTitle,
                # Since drm protection we don't know the number of pages...
                summary = u'Vidare till n�sta sida',
                art     = art
            )
        )

    if len(oc) < 1:
        oc.header  = NO_PROGRAMS_FOUND_HEADER
        oc.message = NO_PROGRAMS_FOUND_MESSAGE

    return oc

####################################################################################################
@route(PREFIX + '/Search')
def Search(query, title):
    oc = ObjectContainer(title2 = unicode(title))

    unquotedQuery = query
    query = String.Quote(query)
    
    for episodeReq in [False, True]:
        videos_oc = TV4ShowVideos(
            title = unicode(title),
            showId = '',
            art = None,
            episodeReq = episodeReq,
            query = query
        )
        
        if len(videos_oc) > 0:
            if episodeReq:
                title = 'Hela avsnitt'
            else:
                title = 'Klipp'
            hits = JSON.ObjectFromURL(GetShowVideosURL(episodes = episodeReq, query = query))
            title = title + "(%i)" % hits['total_hits']
            oc.add(
                DirectoryObject(
                    key = 
                        Callback(
                            TV4ShowVideos,
                            title = title,
                            showId = '',
                            art = None,
                            episodeReq = episodeReq,
                            query = query
                        ),
                    title = title
                )
            )

    programs_oc = TV4Shows(title = unicode(title), query = query)
    for object in programs_oc.objects:
        oc.add(object)
    
    if len(oc) < 1:
        oc.header  = unicode("Sökresultat"),
        oc.message = unicode("Kunde ej hitta något för '%s'" % unquotedQuery)
        
    return oc

####################################################################################################
def Videos(oc, videos, date_range = None, strip_show = False):

    for video in videos['results']:
        if 'is_drm_protected' in video:
            if video['is_drm_protected']:
                continue
        
        video_is_premium_only = video['availability']['availability_group_free'] == '0' or not video['availability']['availability_group_free']
        
        if Prefs['onlyfree'] and not Prefs['premium'] and video_is_premium_only:
            continue
                
        url = TEMPLATE_VIDEO_URL % ('program', String.Quote(video['program_nid']), str(video['id']))
        title = unicode(video['title'])
        summary = unicode(video['description'])
        thumb = video['image']
        art = video['program']['logo'] if 'logo' in video['program'] else None
        duration = int(video['duration']) * 1000
        originally_available_at = Datetime.ParseDate(video['broadcast_date_time'].split('T')[0]).date()
        show = unicode(video['program']['name'])

        if date_range:
            (today, too_late) = date_range
            if 'broadcast_date_time' in video:
                broadcast_time = str(video['broadcast_date_time'])
                ondate = re.sub("T.+", "", broadcast_time).replace("-", "")
                if today > ondate or ondate > too_late:
                    # Only interested in broadcasts within given interval
                    continue
                if not today in ondate:
                    title = unicode("Imorgon " + title)
                else:
                    ontime = re.sub(".+T([0-9]+:[0-9]+).+", "\\1 ", broadcast_time)
                    title = unicode(ontime + title)
        else:
            # Only add availability for non Live Events
            summary = unicode(GetAvailability(video) + summary)
            # Strip show name from title
            tmp_show = re.sub(" - Klipp", "", show)
            if strip_show and re.search(r"\b%s\b" % tmp_show, title):
                title = re.sub(tmp_show+"[ 	\-,:]*(.+)", "\\1", title)

        if not Prefs['onlyfree'] and not Prefs['premium'] and video_is_premium_only: 
            oc.add(
                DirectoryObject(
                    key = Callback(TV4PremiumRequired),
                    title = title + " (Premium)",
                    summary = summary,
                    thumb = thumb,
                    art = art,
                    duration = duration
                )
            )
        else:
            oc.add(
                EpisodeObject(
                    url = url,
                    title = title,
                    summary = summary,
                    thumb = thumb,
                    art = art,
                    duration = duration,
                    originally_available_at = originally_available_at,
                    show = show
                )
            )

    return oc

###################################################################################################
def Programs(oc, programs):
    for program in programs['results']:
        oc.add(
            DirectoryObject(
                key =
                    Callback(
                        TV4ShowChoice,
                        title = program["name"],
                        showId = unicode(program["nid"]),
                        art = program["logo"] if 'logo' in program else None,
                        thumb = program["program_image"],
                        summary = program["description"]
                    ),
                title = unicode(program["name"]),
                summary = unicode(program["description"]),
                thumb = program["program_image"],
                art = program["logo"] if 'logo' in program else None
            )
        )
    
    return oc

###################################################################################################
def GetProgramsURL(page, category = '', query = ''):
    if category is None:
        category = ''

    url = API_BASE_URL + '/play/programs?per_page=%s&page=%s&category=%s' % (ITEMS_PER_PAGE, page, String.Quote(category))
    
    if query:
        url = url + '&q=%s' % query
    
    if Prefs['onlyfree'] and not Prefs['premium']:
        url = url + '&is_premium=false'

    return url
    
###################################################################################################
def GetShowVideosURL(episodes, id = '', query = '', page = 1):
    if id is None:
        id = ''
    
    url = API_BASE_URL + '/play/video_assets?is_live=false&page=%s&platform=web&node_nids=%s&per_page=%s' % (page, id, ITEMS_PER_PAGE)
    
    if query:
        url = url + '&q=%s' % String.Quote(query)

    if episodes:
        url = url + '&type=episode'
    else:
        url = url + '&type=clip'
        
    if Prefs['onlyfree'] and not Prefs['premium']:
        url = url + '&is_premium=false'
        
    return url

###################################################################################################
def GetMostWatchedURL(episodes = True):
    url = API_BASE_URL + '/play/video_assets/most_viewed?page=1&is_live=false&sort=broadcast_date_time&platform=web&per_page=%s&sort_order=desc' % ITEMS_PER_PAGE
 
    if episodes:
        url = url + '&type=episode'
    else:
        url = url + '&type=clip'
    
    if Prefs['onlyfree'] and not Prefs['premium']:
        url = url + '&is_premium=false'
        
    return url
    
###################################################################################################
def GetListingsURL(date = ""):
    url = API_BASE_URL + '/tvdata/listings/TV4?date=%s' % date
        
    if Prefs['onlyfree'] and not Prefs['premium']:
        url = url + '&premium=false'
        
    return url
    
###################################################################################################
def GetVideosURL(vman_ids):
    url = API_BASE_URL + '/play/video_assets?id=%s' % vman_ids
        
    if Prefs['onlyfree'] and not Prefs['premium']:
        url = url + '&is_premium=false'
        
    return url

###################################################################################################
def GetLiveURL(today, too_late):

    url = API_BASE_URL + '/play/video_assets?broadcast_from=%s&broadcast_to=%s&is_live=true&platform=web&sort=broadcast_date_time&sort_order=asc&per_page=%s' % (today, too_late, ITEMS_PER_PAGE)
    
    return url

###################################################################################################
def GetAvailability(video):

    if video['availability']['human'] != None and re.search("\([0-9]+ dagar till\)",video['availability']['human']):
        availabilty = u'Tillg�nglig: ' + re.sub(".+\(([0-9]+ dagar) till\).+","\\1. \r\n\r\n",video['availability']['human'])
    elif video['availability']['availability_group_free'] != None and video['availability']['availability_group_free'] != "0":
        availabilty = u'Tillg�nglig: ' + video['availability']['availability_group_free'] + " dagar. \r\n\r\n"
    elif video['availability']['availability_group_premium'] != None:
        availabilty = u'Tillg�nglig: ' + video['availability']['availability_group_premium'] + " dagar. \r\n\r\n"
    else:
        availabilty = ""
    Log("JTDEBUG availabilty:%r" % availabilty)
    return availabilty

####################################################################################################
def sortOnAirData(Objects):
    for obj in Objects.objects:
        Log("JTDEBUG type of object %r" % obj.content)
        if obj.originally_available_at == None:
            return Objects.objects.reverse()
    return Objects.objects.sort(key=lambda obj: (obj.originally_available_at,obj.title))

####################################################################################################
def GetNavigationItems(offset,total_hits):
    lastPage = (total_hits/ITEMS_PER_PAGE) + 1
    if (offset + ITEMS_PER_PAGE) < total_hits:
        nextPage = (offset / ITEMS_PER_PAGE) + 2
        currPage = nextPage - 1
    else:
        nextPage = None
        currPage = lastPage
    prevPage = currPage - 1

    if currPage == 1 and lastPage > 2:
        # On first - previous page is "last" page
        previousItem = (ITEMS_PER_PAGE*(lastPage-1), "<-Sista", u'G� till sista sidan, sida ' + str(lastPage))
    elif currPage > 1:
        # Prepend Previous
        previousItem = (offset-ITEMS_PER_PAGE, u'<-F�reg�ende', "Tillbaka till sida " + str(currPage-1) + " av " + str(lastPage))
    else:
        previousItem = None

    if nextPage:
        # Add Next
        nextItem = (offset + ITEMS_PER_PAGE, u'N�sta->', "Vidare till sida " + str(nextPage) + " av " + str(lastPage))
    elif lastPage > 2:
        # On last - "next is first"
        nextItem = (0, u'F�rsta->', u'Vidare till f�rsta sidan')
    else:
        nextItem = None

    return (previousItem, nextItem)

####################################################################################################
def AddTV4ShowVideosNavigationDirs(oc,page,total_hits,title,showId,art,episodeReq,query):

    # Offset starts at 0 - page at 1...
    (previousItem, nextItem) = GetNavigationItems((page-1)*ITEMS_PER_PAGE, total_hits)
    if previousItem:
        (previousOffset, previousTitle, previousSummary) = previousItem
        # Prepend PreviousItem directory
        oc.objects.reverse()
        oc.add(DirectoryObject(
                key     = Callback(TV4ShowVideos,
                                   title      = title, 
                                   showId     = showId, 
                                   art        = art, 
                                   episodeReq = episodeReq, 
                                   query      = query, 
                                   page       = (previousOffset/ITEMS_PER_PAGE)+1
                                   ),
                title   = previousTitle,
                summary = previousSummary,
                art     = art
                )
               )
        oc.objects.reverse()
    if nextItem:
        (nextOffset, nextTitle, nextSummary) = nextItem
        # Append NextItem directory
        oc.add(NextPageObject(
                key     = Callback(TV4ShowVideos,
                                   title      = title, 
                                   showId     = showId, 
                                   art        = art, 
                                   episodeReq = episodeReq, 
                                   query      = query, 
                                   page       = (nextOffset/ITEMS_PER_PAGE)+1
                                   ),
                title   = nextTitle,
                summary = nextSummary,
                art     = art
                )
               )
    return oc
