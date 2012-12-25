
import os, re, sys
import urllib, urllib2, HTMLParser
import xbmcgui, xbmcplugin, xbmcaddon
from mindmade import *
import simplejson
from BeautifulSoup import BeautifulSoup

#
# constants definition
############################################
PLUGINID = "plugin.video.sf-videoportal"

# plugin handle
pluginhandle = int(sys.argv[1])

# plugin modes
MODE_SENDUNGEN       = "sendungen"
MODE_SENDUNGEN_ALLTOPICS = "sendungen_alltopics"
MODE_SENDUNGEN_TOPIC = "sendungen_topic"
MODE_SENDUNG         = "sendung"
MODE_VERPASST        = "verpasst"
MODE_VERPASST_DETAIL = "verpasst_detail"
MODE_CHANNEL_LIST    = "channel_list"
MODE_CHANNEL         = "channel"
MODE_PLAY            = "play"

# parameter keys
PARAMETER_KEY_MODE = "mode"
PARAMETER_KEY_ID = "id"
PARAMETER_KEY_URL = "url"
PARAMETER_KEY_TITLE = "title"
PARAMETER_KEY_POS   = "pos"

ITEM_TYPE_FOLDER, ITEM_TYPE_VIDEO = range(2)
BASE_URL = "http://www.srf.ch/"
BASE_URL_PLAYER = "http://www.srf.ch/player/tv"
# for some reason, it only works with the old player version.
FLASH_PLAYER = "http://www.videoportal.sf.tv/flash/videoplayer.swf"
#FLASH_PLAYER = "http://www.srf.ch/player/tv/flash/videoplayer.swf"

settings = xbmcaddon.Addon( id=PLUGINID)

LIST_FILE = os.path.join( settings.getAddonInfo( "path"), "resources", "list.dat")
listItems = []

# DEBUGGER
#REMOTE_DBG = False 

# append pydev remote debugger
#if REMOTE_DBG:
#    # Make pydev debugger works for auto reload.
#    # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
#    try:
#        import pysrc.pydevd as pydevd
#    # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse console
#        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True)
#    except ImportError:
#        sys.stderr.write("Error: " +
#            "You must add org.python.pydev.debug.pysrc to your PYTHONPATH.")
#        sys.exit(1)

#
# utility functions
############################################

# Log NOTICE

def parameters_string_to_dict( parameters):
    ''' Convert parameters encoded in a URL to a dict. '''
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                paramDict[paramSplits[0]] = urllib.unquote( paramSplits[1])
    return paramDict


def addDirectoryItem( type, name, params={}, image="", total=0):
    '''Add a list item to the XBMC UI.'''
    if (type == ITEM_TYPE_FOLDER):
        img = "DefaultFolder.png"
    elif (type == ITEM_TYPE_VIDEO):
        img = "DefaultVideo.png"

    name = htmldecode( name)
    params[ PARAMETER_KEY_TITLE] = name
    li = xbmcgui.ListItem( name, iconImage=img, thumbnailImage=image)
            
    if (type == ITEM_TYPE_VIDEO):
#        li.setProperty( "IsPlayable", "true")
        li.setProperty( "Video", "true")
        global listItems
        listItems.append( (name, params, image))
    
    params_encoded = dict()
    for k in params.keys():
        params_encoded[k] = params[k].encode( "utf-8")
    url = sys.argv[0] + '?' + urllib.urlencode( params_encoded)
    
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder = (type == ITEM_TYPE_FOLDER), totalItems=total)


#
# parsing functions
############################################

def getIdFromUrl( url):
    return re.compile( '[\?|\&]id=([0-9a-z\-]+)').findall( url)[0]

def getUrlWithoutParams( url):
    return url.split('?')[0]


def getJSONForId( id):
    json_url = BASE_URL + "/webservice/cvis/segment/" + id + "/.json?nohttperr=1;omit_video_segments_validity=1;omit_related_segments=1"
    url = fetchHttp( json_url).split( "\n")[1]
    json = simplejson.loads( url)
    return json


def getVideoFromJSON( json):
    streams = json["streaming_urls"]
    sortedstreams = sorted( streams, key=lambda el: int(el["bitrate"]))

    quality = int(settings.getSetting( id="quality"))
    if (quality >= len(sortedstreams)):
        quality = len(sortedstreams)-1;
    
    return sortedstreams[ quality]["url"] + " swfvfy=true swfurl=" + FLASH_PLAYER

def getThumbnailForId( id):
    thumb = BASE_URL + "webservice/cvis/videogroup/thumbnail/" + id
    return thumb


#
# content functions
############################################


#
# mode handlers
############################################

def show_root_menu():
    addDirectoryItem( ITEM_TYPE_FOLDER, "Sendungen", {PARAMETER_KEY_MODE: MODE_SENDUNGEN})
    addDirectoryItem( ITEM_TYPE_FOLDER, "Themen", {PARAMETER_KEY_MODE: MODE_SENDUNGEN_ALLTOPICS})
    addDirectoryItem( ITEM_TYPE_FOLDER, "Sendung verpasst?", {PARAMETER_KEY_MODE: MODE_VERPASST})
    addDirectoryItem( ITEM_TYPE_FOLDER, "Channels", {PARAMETER_KEY_MODE: MODE_CHANNEL_LIST})
    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def show_sendungen():
    url = BASE_URL_PLAYER + "/sendungen"
    soup = BeautifulSoup( fetchHttp( url))
    
    for show in soup.findAll( "div", "az_item"):
        url = show.find( "a")['href']
        title = show.find( "img", "az_thumb")['alt']
        id = getIdFromUrl( url)
        image = getThumbnailForId( id)
        addDirectoryItem( ITEM_TYPE_FOLDER, title, {PARAMETER_KEY_MODE: MODE_SENDUNG, PARAMETER_KEY_ID: id, PARAMETER_KEY_URL: url }, image)

    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def show_sendungen_alltopics():
    url = BASE_URL_PLAYER + "/sendungen"
    soup = BeautifulSoup( fetchHttp( url, {"sort": "topic"}))

    topicNavigation = soup.find( "div", {"id": "topic_navigation"})
    for topic in topicNavigation.findAll( "span"):
        title = topic.text
        onClick = topic['onclick']
        id = re.compile( '(az_unit_[a-zA-Z0-9_]*)').findall(onClick)[0]
        addDirectoryItem( ITEM_TYPE_FOLDER, title, {PARAMETER_KEY_MODE: MODE_SENDUNGEN_TOPIC, PARAMETER_KEY_ID: id})

    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def show_sendungen_topic( params):
    selected_topic = params.get( PARAMETER_KEY_ID)
    url = BASE_URL_PLAYER + "/sendungen"
    soup = BeautifulSoup( fetchHttp( url, {"sort": "topic"}))

    topic = soup.find( "div", { "id" : selected_topic})
    for show in topic.findAll( "div", "az_item"):
        url = show.find( "a")['href']
        title = show.find( "img", "az_thumb")['alt']
        id = getIdFromUrl( url)
        image = getThumbnailForId( id)
        addDirectoryItem( ITEM_TYPE_FOLDER, title, {PARAMETER_KEY_MODE: MODE_SENDUNG, PARAMETER_KEY_ID: id, PARAMETER_KEY_URL: url }, image)

    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def show_sendung( params):
    sendid = params.get( PARAMETER_KEY_ID)
    urlParam = params.get( PARAMETER_KEY_URL)
    url = BASE_URL + getUrlWithoutParams( urlParam)
    soup = BeautifulSoup( fetchHttp( url, {"id": sendid}))

    for show in soup.findAll( "div", "sendung_item"):
        title = show.find( "div", "title").text
        titleDate = show.find( "div", "title_date").text
        image = getUrlWithoutParams( show.find( "img")['src'])
        a = show.find( "a")
        id = getIdFromUrl( a['href'])
        addDirectoryItem( ITEM_TYPE_VIDEO, title + " " + titleDate, {PARAMETER_KEY_MODE: MODE_PLAY, PARAMETER_KEY_ID: id }, image)

    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def show_verpasst():
    url = BASE_URL_PLAYER + "/verpasst"

    timestamp = 999999999999 # very high to get today.
    for x in range(0, 7):
        soup = BeautifulSoup( fetchHttp( url, { "date": timestamp}))
        rightDay = soup.find( "div", { "id": "right_day"})
        title = rightDay.find( "h2").text
        timestamp = long(rightDay.find( "input", "timestamp")['value'])
        addDirectoryItem( ITEM_TYPE_FOLDER, title, {PARAMETER_KEY_MODE: MODE_VERPASST_DETAIL, PARAMETER_KEY_POS: str(timestamp)})
        timestamp = (timestamp - (24*60*60))

    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def show_verpasst_detail( params):
    url = BASE_URL_PLAYER + "/verpasst"
    timestamp = params.get( PARAMETER_KEY_POS)
    soup = BeautifulSoup( fetchHttp( url, { "date": timestamp}))
    
    rightDay = soup.find( "div", { "id": "right_day"})
    
    for show in rightDay.findAll( "div", "overlay_sendung_item"):
        title = show.find( "a", "title").text
        time = show.find( "p", "time").text
        image = getUrlWithoutParams( show.find( "img")['src'])
        a = show.find( "a")
        id = getIdFromUrl( a['href'])
        addDirectoryItem( ITEM_TYPE_VIDEO, time + ": " + title, {PARAMETER_KEY_MODE: MODE_PLAY, PARAMETER_KEY_ID: id }, image)

    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def show_channel_list():
    url = BASE_URL_PLAYER + "/themen"
    soup = BeautifulSoup( fetchHttp( url))

    for topic in soup.findAll( "div", "themen_metadata"):
        title = topic.find("h2").string
        addDirectoryItem( ITEM_TYPE_FOLDER, title, {PARAMETER_KEY_MODE: MODE_CHANNEL, PARAMETER_KEY_ID: title})

    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def show_channel( params):
    selected_topic = params.get( PARAMETER_KEY_ID)
    url = BASE_URL_PLAYER + "/thema/" + selected_topic
    soup = BeautifulSoup( fetchHttp( url, {"cid": selected_topic}))

    for show in soup.findAll( "div", "sendung_box_item"):
        url = show.find( "a")['href']
        title = show.find( "div", "title").text
        id = getIdFromUrl( url)
        image = getUrlWithoutParams(show.find( "img")['src'])
        addDirectoryItem( ITEM_TYPE_VIDEO, title, {PARAMETER_KEY_MODE: MODE_PLAY, PARAMETER_KEY_ID: id}, image)

    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)
        

#
# xbmc entry point
############################################

sayHi()

# read parameters and mode
params = parameters_string_to_dict(sys.argv[2])

mode = params.get(PARAMETER_KEY_MODE, "0")

# depending on the mode, call the appropriate function to build the UI.
if not sys.argv[2]:
    # new start
    ok = show_root_menu()
elif mode == MODE_SENDUNGEN:
    ok = show_sendungen()
elif mode == MODE_SENDUNGEN_ALLTOPICS:
    ok = show_sendungen_alltopics()
elif mode == MODE_SENDUNGEN_TOPIC:
    ok = show_sendungen_topic( params)
elif mode == MODE_SENDUNG:
    ok = show_sendung(params)
elif mode == MODE_VERPASST:
    ok = show_verpasst()
elif mode == MODE_VERPASST_DETAIL:
    ok = show_verpasst_detail(params)
elif mode == MODE_CHANNEL_LIST:
    show_channel_list()
elif mode == MODE_CHANNEL:
    show_channel( params)
elif mode == MODE_PLAY:
    id = params["id"]
    json = getJSONForId( id)
    url = getVideoFromJSON( json)
    if "mark_in" in json.keys( ):
        start = json["mark_in"]
    elif "mark_in" in json["video"]["segments"][0].keys():
        start = json["video"]["segments"][0]["mark_in"]
    else: start = 0
    li = xbmcgui.ListItem( params[ PARAMETER_KEY_TITLE])
    li.setProperty( "IsPlayable", "true")
    li.setProperty( "Video", "true")
    li.setProperty( "startOffset", "%f" % (start))
    xbmc.Player().play( url, li)
