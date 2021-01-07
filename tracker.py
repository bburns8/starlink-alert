import os
import math
from dotenv import load_dotenv
load_dotenv()
from skyfield.api import Topos, load
from datetime import timedelta
from pytz import timezone
from twilio.rest import Client
# load the satellite dataset from Celestrak
starlink_url = 'https://celestrak.com/NORAD/elements/starlink.txt'
starlinks = load.tle_file(starlink_url)
print ('Loaded', len(starlinks), 'satellites')
# update city location and timezone
location = Topos('47.6 N', '-122.2 W')
tz = timezone('US/Pacific')
# establish time window of opportunity
ts = load.timescale()
t0 = ts.now()
t1 = ts.from_datetime(t0.utc_datetime()+ timedelta(hours=2))
# loop through satellites to find next sighting
first_sighting = {}
for satellite in starlinks:
   # filter out farthest satellites and NaN elevation
   elevation = satellite.at(t0).subpoint().elevation.km
   isNan = math.isnan(elevation)
   if elevation > 400 or isNan: continue
   print ('considering: {} at {}km'.format(
       satellite.name,
       round(elevation)
   ))
   # find and loop through rise / set events
   t, events = satellite.find_events(location, t0, t1, altitude_degrees=30.0)
   for ti, event in zip(t, events):
      
       # check if satellite visible to a ground observer
       eph = load('de421.bsp')
       sunlit = satellite.at(t1).is_sunlit(eph)
       if not sunlit: continue
       # filter by moment of greatest altitude - culminate
       name = ('rise above 30°', 'culminate', 'set below 30°')[event]
       if (name != 'culminate'): continue
          
       # find earliest time for next sighting
       if (not first_sighting) or (ti.utc < first_sighting['time']):
           first_sighting['time_object'] = ti
           first_sighting['time'] = ti.utc
           first_sighting['satellite'] = satellite
if (first_sighting): 
   # create body for SMS  
   next_sighting = ('next sighting: {} {}'.format(
       first_sighting['satellite'].name,
       first_sighting['time_object'].astimezone(tz).strftime('%Y-%m-%d %H:%M')
   ))
   # send SMS via Twilio if upcoming sighting
   account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
   auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
   client = Client(account_sid, auth_token)
   message = client.messages.create(
       body=next_sighting,
       from_=os.environ.get('TWILIO_PHONE_NUMBER'),
       to=os.environ.get('MY_PHONE_NUMBER')
   )
   print ('Message sent:', message.sid, next_sighting)
else:
   print ('No upcoming sightings')