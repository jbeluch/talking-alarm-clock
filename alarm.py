#!/usr/bin/env python
#talking alarm clock
#6/2/2010 jon@jonathanbeluch.com
from libs.BeautifulSoup import BeautifulStoneSoup as BSS
import urllib2
from string import Template
from ConfigParser import ConfigParser
import re
#collect data from each source, enter into the main festival script
#1. download data
#2. compose template for specific data
#3. compose master template comprised of all small templates


class GMail(object):
    path = 'libs/gmail/'
    url = 'https://mail.google.com/mail/feed/atom'

    def __init__(self, username, password):
        self.username = username
        self.password = password        
        self.read_templates()

    def read_templates(self):
        f = open('templates/email.template', 'r')
        self.email_template = Template(f.read())
        f.close()
        f = open('templates/gmail.template', 'r')
        self.gmail_template = Template(f.read())
        f.close()

    def generate_output(self):
        #download feed
        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password('New mail feed', self.url, self.username,
                                  self.password)
        opener = urllib2.build_opener(auth_handler)
        u = opener.open(self.url)
        email_xml = BSS(u.read(), selfClosingTags=['link'])
        u.close()
    
        #parse email subjects and sender
        email_tags = email_xml.findAll('entry') 
        emails = []
        
        #generate email strings
        for e in email_tags:
            subs = {'sender': e.author.nameTag.text,
                    'subject': e.title.text}
            email_text = self.email_template.substitute(subs)
            emails.append(email_text)

        subs = {'unread_count': email_xml.fullcount.text,
                'emails': '\n'.join(emails)}
        return self.gmail_template.substitute(subs)

class GoogleCalendar(object):
    def __init__(self, url):
        self.url = url

    def generate_output(self):
        self._get_events()
        return 'done' 

    def _get_events(self):
        u = urllib2.urlopen(self.url)
        events = BSS(u.read())
        u.close()
        event_tags = events.findAll('category')
        for e in event_tags:
            print e
            print ''
    
class Weather(object):
    url = 'http://weather.yahooapis.com/forecastrss?w=12761347'

    def __init__(self):
        pass

    def generate_output(self):
        xml = BSS(download_page(self.url))     
        ys = xml.findAll(re.compile('yweather'))
        self._parse_weather_data(xml)
        #read templates
        #substitute with self.wdata
        #write out template
        
    def _parse_weather_data(self, xml):
        wdata = {}
        i = 1
        for y in xml.findAll(re.compile('yweather')):
            name = y.name[9:]
            if name == 'forecast': 
                name = 'forecast%s' % i
                i = i + 1
            [wdata.update({'%s_%s' % (name, k): v}) for k, v in y.attrs]
        self.wdata = wdata

def create_output(config):
    #subs = {} #gmail gmail = GMail(config.get('gmail', 'username'),
    #              config.get('gmail', 'password'))
    #subs['gmail'] = gmail.generate_output()    
    Weather().generate_output()

    #google calendar
    #url = ''
    #gcal = GoogleCalendar(url)
    #subs['gcal'] = gcal.generate_output()
    #print subs

def get_config_options():
    config = ConfigParser()
    config.readfp(open('.passwd'))
    return config

def download_page(url):
    return urllib2.urlopen(url).read()

if __name__ == '__main__':
    config = get_config_options()
    create_output(config)

