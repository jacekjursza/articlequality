#!/usr/bin/env python

"""
Gather data on articles

Factors done:

  * Size of content
  * has category
  * has image
  * has sections
  * templates
  * structured data
  * size of wikia
  * likes/facebook shares

Potential factors:

  Labels: Stub, featured
    
  Revision based:    
    place in articles life cycle
    multiple author
    number of edits / editors
    creator

  Content based: 
    Diversity of words words in content
    has inbound and outbound links
    no. of redirects
    info boxes
    comments / talk pages
    
  Popularity:  
    page views
    page rank
    wiki's WAM
    link from the main page
    link from hubs
    wiki has promote
    Google +1

Input file - CSV format, first row skipped:
URL in first column
Article quality (0-100) in last column
Rest of columns ignored

"""

import os, csv, sys, itertools, operator, codecs, collections, requests, json
from twisted.internet import defer, threads
from twisted.python import log
from twisted.web import client

class Api(object):
  def __init__(self, api, **defaults):
    self.api = api
    self.defaults = {'format':'json'}
    self.defaults.update(defaults)

  def __call__(self, **kwargs):
    params = self.defaults.copy()
    params.update(kwargs)
    r = requests.get(self.api, params=sorted(params.items()))
    if not r.ok:raise Exception(r.text)
    json = r.json()
    if not json: raise Exception(r.text)
    return json
  
    
class FbLinks(Api):
  def __init__(self, url):
    super(FbLinks, self).__init__("http://api.facebook.com/method/fql.query",
          query = '''select total_count from link_stat where url="'%s'"''' % url)
    
  def __call__(self):
    return super(FbLinks, self).__call__()[0]['total_count']
  
def prettyPrint(obj):
  return json.dumps(obj, indent=2)

class Article(object):
  print_json = False
  
  def __init__(self, url, quality):
    self.url = url
    self.quality = quality
    (self.wikiDomain, self.titlePath) = self.url.split("/wiki/")
    self.title = self.titlePath.replace("_", " ")
      
  def fetch(self):
    self.mwApi = Api(self.wikiDomain + "/api.php", action='query', titles=self.title)
    self.info = self.mwApi(
      prop='info|images|categories|links|templates',
      meta='siteinfo',
      siprop='statistics',
      pllimit=20
    )
    self.statistics = self.info['query']['statistics']
    self.page = self.info['query']['pages'].values()[0]
    self.pageid = self.page['pageid']
    self.likes = FbLinks(self.url)()
    self.structured = Api(self.wikiDomain + "/wikia.php?controller=ArticlesApi&method=getAsSimpleJson")(id=self.pageid)
    values = [c(self) for c in self.columns()]    
    return values
  
  def column_url(self):
    """URL of article"""
    return self.url

  def column_title(self):
    """Wiki name"""
    return self.title

  def column_quality(self):
    """Quality percentile"""
    return self.quality    
  
  def column_length(self):
    """Article length"""
    return self.page['length']
  
  def count(self, key):
    return len(self.page.get(key, ()))
  
  def column_image_count(self):
    """Image count"""
    return self.count('images')
  
  def column_categories(self):
    """Category count"""
    return self.count('categories')
  
  def column_outbound(self):
    """Outbound link count"""
    return self.count('links')

  def column_templates(self):
    """Used template count"""
    return self.count('templates')
  
  def column_wikia_articles(self):
    """Count of articles on this Wikia"""
    return self.statistics['articles']
  
  def column_wikia_edits(self):
    """Count of edits on this Wikia"""
    return self.statistics['edits']
  
  def column_wikia_activeusers(self):
    """Count of active users on this Wikia"""
    return self.statistics['activeusers']
  
  def column_wikia_editsperuser(self):
    """Average edits per user on this Wikia"""
    if self.statistics['activeusers']:
      return self.statistics['edits'] / self.statistics['activeusers']
    
  def column_fb_links(self):
    """Facebook total shares"""
    return self.likes
  
  def column_section_count(self):
    """Section count"""
    sections = self.structured.get('sections', ()) # count top-level only 
    return len(sections)
  
  _columns = [    
    column_url, column_title, column_quality, column_length, column_image_count, column_categories,
    column_outbound, column_templates, column_wikia_articles, column_wikia_edits,
    column_wikia_activeusers, column_wikia_editsperuser, column_fb_links, column_section_count,   
  ]

  def json_info(self):
    """MW API result"""
    return prettyPrint(self.info)

  def json_structure(self):
    """asSimpleJson API result"""
    return prettyPrint(self.structured)
     

  _json_columns = [
    json_info, json_structure
  ]
  
  
  @classmethod
  def columns(cls):    
    return cls._columns + cls._json_columns if cls.print_json else cls._columns
      

def main(args):
  if '--json' in args: Article.print_json = True
  header = [getattr(x, "__doc__", getattr(x, "__name__")) for x in Article.columns()]
  reader = csv.reader(sys.stdin)
  writer = csv.writer(sys.stdout, quoting=csv.QUOTE_NONNUMERIC)  
  writer.writerow(header)
  input = [(line[0], line[-1]) for line in reader][1:] # skip first row (header)
  if '--single' in args: input = input[:1] # test run on one row
  dl = defer.DeferredList([threads.deferToThread(Article(*x).fetch) for x in input])
  @dl.addCallback
  def write(rows):
    successes = [row[1] for row in rows if row[0]]
    writer.writerows(successes)
    failures = [row[1] for row in rows if not row[0]]
  @dl.addErrback
  def cb(failure):
    log.msg(failure)
  dl.addBoth(lambda x: reactor.stop())


if __name__ == "__main__":
  from twisted.internet import reactor
  reactor.callWhenRunning(main, sys.argv)
  reactor.run()
