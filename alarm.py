#!/usr/bin/env python
#talking alarm clock
#6/2/2010 jon@jonathanbeluch.com
from libs.BeautifulSoup import BeautifulStoneSoup as BSS
import urllib2
import datetime
from string import Template
from libs.rfc3339 import parse_datetime, parse_date, datetimetostr
from ConfigParser import ConfigParser
import re
import os
import urllib
#collect data from each source, enter into the main festival script
#1. download data
#2. compose template for specific data
#3. compose master template comprised of all small templates


class GMail(object):
    #todo - pass all available gmail feed values to the template
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

    def __init__(self, options):
        url = 'http://weather.yahooapis.com/forecastrss?w=%s'
        self.url = url % options['code'] 
        self.options = options
        self.template_fn = options['template']

    def generate_output(self):
        xml = BSS(download_page(self.url))     

        #read templates
        self.template = read_template(self.template_fn) 

        #parse data
        self.weather_data = self._parse_weather_data(xml)

        #substitute with self.wdata
        self.output = self.template.substitute(self.weather_data)
        return self.output        

    def _parse_weather_data(self, xml):
        wdata = {}
        i = 1
        for y in xml.findAll(re.compile('yweather')):
            name = y.name[9:]
            if name == 'forecast': 
                name = 'forecast%s' % i
                i = i + 1
            [wdata.update({'%s_%s' % (name, k): v}) for k, v in y.attrs]
        return(wdata)

def get_datetime(date_string):
    """takes an rfc3339 formatted date or datetime string and returns the apppropriate date or datetime object"""
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

    print output
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

