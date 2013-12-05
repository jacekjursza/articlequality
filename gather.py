#!/usr/bin/env python

"""
Gather data on articles

Factors proposal

  * Size of content
    Labels: Stub, featured
    place in articles life cycle
    Diversity of words words in content
  * has category
    has inbound and outbound links
  * has image
    has sections
    page views
    multiple author
    page rank
    info boxes
  *  templates
    structured data
    creator
  *  size of wikis
    wiki's WAM
    wiki has promote
    no. of redirects
    number of edits / editors
    comments / talk pages
    link from the main page
    link from hubs
    likes / +1


Factors working at the moment are marked with * above.
"""

import os, csv, sys, itertools, operator, codecs, collections, requests
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
    if not r.json(): raise Exception(r.text)
    return r.json()
  
    
class FbLikes(object):
  def __init__(self, url):
    self.url = url
    
  def __call__(self):
    r = requests.get("http://api.facebook.com/method/fql.query", params=
          {'query': '''select like_count from link_stat where url="'%s'"''' % self.url,
           'format': 'json'})
    if not r.ok:raise Exception(r.text)
    if not r.json(): raise Exception(r.text)
    return r.json()[0]['like_count']   

class Article(object):
  print_json = False
  
  def __init__(self, url):
    self.url = url
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
    self.likes = FbLikes(self.url)()
    #self.wikiaApi = Api(self.wikiDomain + "/api/v1/Related
    


    values = [c(self) for c in self.columns]
    if self.print_json: values.append(repr(self.info))
    return values

  def column_url(self):
    """URL of article"""
    return self.url

  def column_title(self):
    """Wiki name"""
    return self.title
  
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
    """Outbound links"""
    return self.count('links')

  def column_templates(self):
    """Outbound templates"""
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
    
  def column_likes(self):
    """Facebook likes"""
    return self.likes
  
  columns = [
    column_url, column_title, column_length, column_image_count, column_categories,
    column_outbound, column_templates, column_wikia_articles, column_wikia_edits,
    column_wikia_activeusers, column_wikia_editsperuser, column_likes
  ]
      

def main(args):
  if '--json' in args: Article.print_json = True
  header = [getattr(x, "__doc__", getattr(x, "__name__")) for x in Article.columns]
  reader = csv.reader(sys.stdin)  
  writer = csv.writer(sys.stdout, quoting=csv.QUOTE_NONNUMERIC)  
  writer.writerow(header)
  urls = [line[0] for line in reader]
  dl = defer.DeferredList([threads.deferToThread(Article(url).fetch) for url in urls])
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
