#!/usr/bin/env python
#talking alarm clock
#6/2/2010 jon@jonathanbeluch.com
from libs.BeautifulSoup import BeautifulStoneSoup as BSS
from libs.rfc3339 import parse_datetime, parse_date, datetimetostr
from xml.etree import ElementTree as ET
from ConfigParser import ConfigParser
from string import Template
import urllib2
import datetime
import re
import os
import urllib


class GMail(object):
    url = 'https://mail.google.com/mail/feed/atom'

    def __init__(self, options):
        self.username = options['username']
        self.password = options['password']
        self.email_tmpl = read_template(options['email_template'])
        self.gmail_tmpl = read_template(options['gmail_template'])

    def _download_feed(self):
        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password('New mail feed', self.url, self.username,
                                  self.password)
        opener = urllib2.build_opener(auth_handler)
        u = opener.open(self.url)
        data = u.read()
        u.close()
        return data

    def generate_output(self):
        #download email feed and parse xml
        xml = BSS(self._download_feed(), selfClosingTags=['link'])
    
        #for each email, generate output subbing the sender and the subject
        emails = [self.email_tmpl.substitute({'sender': e.author.nameTag.text,
                  'subject': e.title.text}) for e in xml.findAll('entry')]

        #substitute all of the email templates into one output string
        self.output = self.gmail_tmpl.substitute(
            {'unread_count': xml.fullcount.text, 'emails': '\n'.join(emails)})

        return self.output


class GoogleCalendar(object):
    url = 'http://www.google.com/calendar/feeds/%s/private-%s/full-noattendees'

    def __init__(self, options):
        self.username = options['username']
        self.cookie = options['cookie']
        self.url = self.url % (self.username, self.cookie)
        self.allday_tmpl = read_template(options['allday_template'])
        self.timed_tmpl = read_template(options['timed_template'])

    def generate_output(self):
        d = datetime.datetime.now()

        #only request events that start within the next 24 hours
        params = {'start-min': datetimetostr(d),
                  'start-max': datetimetostr(d + datetime.timedelta(1)),
                  'orderby': 'starttime',
                  'sortorder': 'ascending'}
        self.url = '%s?%s' % (self.url, urllib.urlencode(params))
        xml = BSS(download_page(self.url), 
                  selfClosingTags=['category', 'content', 'link'])

        #only parse entry title and start time
        entries = [(e.title.text, 
                    get_datetime(e.find('gd:when')['starttime']))
                    for e in xml.findAll('entry')]
        output = []
        for content, start_time in entries:
            #use different templates for all day events vs events with a start
            #time
            if type(start_time) == datetime.date:
                output.append(self.allday_tmpl.substitute(
                    {'content': content}))
            else:
                output.append(self.timed_tmpl.substitute(
                    {'content': content, 
                     'start_time': start_time.strftime('%I:%M %p')}))
        return ''.join(output) 

    
class Weather(object):
    url = 'http://weather.yahooapis.com/forecastrss?w=%s'
    
    def __init__(self, options):
        self.url = self.url % options['code'] 
        self.options = options
        self.template = read_template(options['template'])

    def generate_output(self):
        #parse data
        self.weather_data = self._parse_weather_data(self.url) 

        #substitute with self.wdata
        self.output = self.template.substitute(self.weather_data)
        return self.output        

    def _parse_weather_data(self, url):
        """takes a yahoo weather url and returns a dict of weather data for
        use in templating"""
        ns = 'http://xml.weather.yahoo.com/ns/rss/1.0'

        #open url and parse rss feed
        xml = ET.parse(urllib.urlopen(url)).getroot()
        tag_attrs = {
            'location': ('city', 'region', 'country'),
            'units': ('temperature', 'distance', 'pressure', 'speed'),
            'wind': ('chill', 'direction', 'speed'),
            'atmosphere': ('humidity', 'visibilitiy', 'pressure', 'rising'),
            'astronomy': ('sunrise', 'sunset'),
            'forecast1': ('low', 'high', 'day', 'date', 'text', 'code'),
            'forecast2': ('low', 'high', 'day', 'date', 'text', 'code'),
            'condition': ('code', 'date', 'temp', 'text')}
        tags = {'location': xml.find('channel/{%s}location' % ns),
                'units': xml.find('channel/{%s}units' % ns),
                'wind': xml.find('channel/{%s}wind' % ns),
                'atmosphere': xml.find('channel/{%s}atmosphere' % ns),
                'astronomy': xml.find('channel/{%s}astronomy' % ns),
                'forecast1': xml.findall('channel/item/{%s}forecast' % ns)[0],
                'forecast2': xml.findall('channel/item/{%s}forecast' % ns)[1],
                'condition': xml.find('channel/item/{%s}condition' % ns)}

        #update the wdata dict with each tag's attributes
        wdata = {}
        for tag_name, tag in tags.items():
            wdata.update(self._parse_attrs(tag, tag_name, tag_attrs[tag_name]))
        return wdata

    def _parse_attrs(self, tag, tag_name, attrs):
        """Returns a dict of attributes and values, the dict key is equal to 
        '<tag_name>_<attribute_name>'."""
        result = {}
        for attr in attrs:
            result['%s_%s' % (tag_name, attr)] = tag.get(attr)
        return result


def get_datetime(date_string):
    """takes an rfc3339 formatted date or datetime string and returns the apppropriate date or datetime object"""
    #if timestampe is found in string, its a datetime else, just date
    if date_string.find('T') > 0:
        return parse_datetime(date_string)
    return parse_date(date_string)

def create_output(config):
    output = {} 

    # Gmail
    gmail = GMail(dict(config.items('gmail')))
    output['gmail'] = gmail.generate_output()

    # Weather
    weather = Weather(dict(config.items('weather')))
    output['weather'] = weather.generate_output()

    # Google Calendar
    gcal = GoogleCalendar(dict(config.items('gcal')))
    output['gcal'] = gcal.generate_output()

    #for now just print to a file, eventually will use a master template here
    with open('output', 'w') as f:
        f.writelines(output.values())

def get_config_options():
    config = ConfigParser()
    config.readfp(open('.config'))
    return config

def read_template(fn):
    """Reads from fn and returns a String.Template object ignoring any lines
    that begin with '#'"""
    with open(fn) as f:
        lines = [line for line in f if line[0] != '#']
    return Template(''.join(lines))

def download_page(url):
    """returns a content string for a given url"""
    return urllib2.urlopen(url).read()

if __name__ == '__main__':
    config = get_config_options()
    create_output(config)

