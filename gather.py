#!/usr/bin/env python

"""
Gather data on articles
"""

import os, csv, sys, itertools, operator, codecs, collections, requests
from twisted.internet import defer, threads
from twisted.python import log

class Api(object):
  def __init__(self, api, **defaults):
    self.api = api
    self.defaults = {'format':'json'}
    self.defaults.update(defaults)

  def __call__(self, **kwargs):
    params = self.defaults.copy()
    params.update(kwargs)    
    r = requests.get(self.api, params=params)
    if not r.ok:raise Exception(r.text)
    if not r.json(): raise Exception(r.text)
    return r.json()


class Article(object):
  def __init__(self, url):
    self.url = url
    (self.wikiDomain, self.titlePath) = self.url.split("/wiki/")
    self.title = self.titlePath.replace("_", " ")
      
  def fetch(self):
    self.mwapi = Api(self.wikiDomain + "/api.php", action='query', titles=self.title)
    self.info = self.mwapi(prop='info|images')['query']['pages'].values()[0]
    #print self.info
    values = [c(self) for c in self.columns]
    return values

  def column_url(self):
    """URL of article"""
    return self.url

  def column_title(self):
    """Wiki name"""
    return self.title
  
  def column_length(self):
    """Article length"""
    return self.info['length']
  
  def column_image_count(self):
    """Image count"""
    return len(self.info.get('images', ()))   
  
  columns = [
    column_url, column_title, column_length, column_image_count
  ]
      

def main():
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
  reactor.callWhenRunning(main)
  reactor.run()
