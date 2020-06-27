import os
import json
import base64
import urllib2
import urlparse
import logging
import pkgutil
from . import Security3, Ldap3

class MethodRequest(urllib2.Request):
    def __init__(self, *args, **kwargs):
        if 'method' in kwargs:
            self._method = kwargs['method']
            del kwargs['method']
        else: self._method = None
        urllib2.Request.__init__(self, *args, **kwargs)

    def get_method(self, *args, **kwargs):
        if self._method is not None: return self._method
        return urllib2.Request.get_method(self, *args, **kwargs)

class Nexus3(object):
    def __init__(self, scr):
        self.scr = scr
        self.log = logging.getLogger(__name__)
        self.path = None
        self.repos = None
        self.repomap = None
        self.ldap = Ldap3()
        self.security = Security3()
        self.url = None
        self.user = None
        self.pasw = None

    def refresh(self, path):
        self.path = None
        self.repos = None
        self.repomap = None
        self.security.initialize()
        self.ldap.initialize()
        if None in (path, self.url, self.user, self.pasw): return True
        self.log.info("Reading repository config from Nexus.")
        try:
            data = self.requestData('service/rest/v1/script')
            if isinstance(data, basestring):
                self.log.info("Retrying with older Nexus API.")
                data = self.requestData('service/siesta/rest/v1/script')
            if isinstance(data, basestring): return data
            path = os.path.abspath(path)
            stores = self.getstores(data)
            repos, repomap = [], {}
            for repo in data['repos']:
                repodata = self.getrepo(repo, stores)
                repos.append(repodata)
                repomap[repodata['id']] = repodata
            self.log.info("Successfully read repository config.")
        except:
            self.log.exception("Error reading repository config.")
            return "Error reading repository config."
        repos.sort(key=lambda x: x['class'])
        if not self.scr.args.disable_security_migration:
            self.ldap.refresh(data)
            secrtn = self.security.refresh(data)
            if secrtn != True: return secrtn
        self.repos = repos
        self.repomap = repomap
        self.path = path
        return True

    def getstores(self, data):
        stores, tmps = {}, []
        for store in data['blobstores']:
            storedata = {}
            storedata['name'] = store['name']
            storedata['type'] = store['type']
            if store['type'] == 'File':
                storedata['paths'] = [store['attributes']['file']['path']]
            else:
                storedata['paths'] = []
            if store['type'] == 'Group':
                tmps.append((storedata, store))
            stores[storedata['name']] = storedata
        for storedata, store in tmps:
            for member in store['attributes']['group']['members']:
                storedata['paths'].extend(stores[member]['paths'])
        return stores

    def getrepo(self, repo, stores):
        # TODO New repodatas:
        # repodata['blackedout']
        # repodata['offline']
        # repodata['remoteuser']
        # repodata['remotepasw']
        # repodata['dockerversion']
        # repodata['metadatalife']
        # repodata['misslife']
        repodata = {}
        repodata['id'] = repo['name']
        repodata['desc'] = None
        repodata['blackedout'] = not repo['config']['online']
        if repo['type'] == 'hosted': repodata['class'] = 'local'
        elif repo['type'] == 'proxy': repodata['class'] = 'remote'
        elif repo['type'] == 'group': repodata['class'] = 'virtual'
        form, layout = repo['format'], repo['format']
        if form == 'raw': form, layout = 'generic', 'simple'
        elif form == 'rubygems': form, layout = 'gems', 'simple'
        elif form == 'maven2': form, layout = 'maven', 'maven-2'
        elif form in ('docker', 'gitlfs', 'pypi', 'yum'): layout = 'simple'
        repodata['type'] = form
        repodata['layout'] = layout + '-default'
        repodata['release'] = False
        repodata['snapshot'] = False
        repodata['behavior'] = 'unique'
        repodata['maxuniquesnapshots'] = None
        attrs = repo['config']['attributes']
        if 'maven' in attrs and 'versionPolicy' in attrs['maven']:
            policy = attrs['maven']['versionPolicy']
            repodata['release'] = policy in ("RELEASE", "MIXED")
            repodata['snapshot'] = policy in ("SNAPSHOT", "MIXED")
        if 'docker' in attrs and 'v1Enabled' in attrs['docker']:
            version = 'V1' if attrs['docker']['v1Enabled'] else 'V2'
            repodata['dockerversion'] = version
        if 'proxy' in attrs:
            if 'metadataMaxAge' in attrs['proxy']:
                repodata['metadatalife'] = 60*attrs['proxy']['metadataMaxAge']
            if 'remoteUrl' in attrs['proxy']:
                repodata['remote'] = attrs['proxy']['remoteUrl']
        if 'negativeCache' in attrs and 'timeToLive' in attrs['negativeCache']:
            ncache = attrs['negativeCache']
            if 'enabled' in ncache and ncache['enabled'] == True:
                repodata['misslife'] = 60*ncache['timeToLive']
        if 'httpclient' in attrs:
            if 'blocked' in attrs['httpclient']:
                repodata['offline'] = attrs['httpclient']['blocked']
            if 'authentication' in attrs['httpclient']:
                auth = attrs['httpclient']['authentication']
                if auth['type'] == 'username':
                    repodata['remoteuser'] = auth['username']
                    repodata['remotepasw'] = auth['password']
        if 'group' in attrs: repodata['repos'] = attrs['group']['memberNames']
        if 'storage' in attrs:
            storename = attrs['storage']['blobStoreName']
            if storename in stores: repodata['storage'] = stores[storename]
        return repodata

    def requestData(self, basepath):
        self.log.info("Attempting to communicate with Nexus server.")
        auth = "Basic " + base64.b64encode(self.user + ':' + self.pasw)
        deppath = self.url[2] + basepath
        delpath = deppath + '/artifactorymigrator'
        runpath = delpath + '/run'
        depurl = urlparse.urlunsplit((self.url[0], self.url[1], deppath, '', ''))
        delurl = urlparse.urlunsplit((self.url[0], self.url[1], delpath, '', ''))
        runurl = urlparse.urlunsplit((self.url[0], self.url[1], runpath, '', ''))
        delheaders = {'User-Agent': 'nex2art', 'Authorization': auth}
        depheaders, runheaders = delheaders.copy(), delheaders.copy()
        depheaders['Content-Type'] = 'application/json'
        runheaders['Content-Type'] = 'text/plain'
        depjson = {'name': 'artifactorymigrator', 'type': 'groovy'}
        groovy = pkgutil.get_data('nex2art', 'resources/plugin.groovy')
        if self.scr.args.disable_security_migration:
            depjson['content'] = groovy.replace('SKIPSEC', 'true')
        else:
            depjson['content'] = groovy.replace('SKIPSEC', 'false')
        depbody = json.dumps(depjson)
        res, data = None, None
        self.log.info("Deploying extraction plugin to Nexus.")
        ex, _ = self.dorequest(depurl, depbody, depheaders, 'POST', "deploy")
        if ex == None:
            try:
                self.log.info("Executing Nexus extraction.")
                ex, res = self.dorequest(runurl, None, runheaders, 'POST', "execute", True)
            finally:
                self.log.info("Deleting extraction plugin from Nexus.")
                self.dorequest(delurl, None, delheaders, 'DELETE', "delete")
            if res != None and 'result' in res: data = json.loads(res['result'])
        if ex != None:
            self.log.error("Error accessing Nexus instance: %s", ex)
            return "Error accessing Nexus instance."
        self.log.info("Successfully fetched Nexus data.")
        return data

    def checkNexus(self):
        state = self.scr.state["Initial Setup"]
        url = state["Nexus URL"].data
        user = state["Nexus Username"].data
        pasw = state["Nexus Password"].data
        nx = self.scr.nexus
        nx.vurl, nx.vuser, nx.vpasw = nx.queryNexus(url, user, pasw)
        newpath = state["Nexus Data Directory"].data
        nx.vpath = self.refresh(newpath)
        self.scr.format.update()

    def queryNexus(self, urlstr, user, pasw):
        self.log.info("Sending system ping to Nexus.")
        url = list(urlparse.urlparse(str(urlstr)))
        if url[0] not in ('http', 'https'): url = None
        elif len(url[2]) == 0 or url[2][-1] != '/': url[2] += '/'
        headers, stat = {'User-Agent': 'nex2art'}, None
        if user != None and pasw != None:
            enc = base64.b64encode(user + ':' + pasw)
            headers['Authorization'] = "Basic " + enc
        if url != None:
            path = url[2] + 'service/metrics/ping'
            nurl = urlparse.urlunsplit((url[0], url[1], path, '', ''))
            self.log.info("Sending request to %s.", nurl)
            try:
                req = urllib2.Request(nurl, None, headers)
                if self.scr.sslnoverify:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    resp = urllib2.urlopen(req, context=ctx)
                else: resp = urllib2.urlopen(req)
                stat = resp.getcode()
            except urllib2.HTTPError as ex:
                msg = "Error connecting to Nexus:\n%s"
                self.log.exception(msg, ex.read())
                stat = ex.code
            except urllib2.URLError as ex:
                self.log.exception("Error connecting to Nexus:")
                stat = ex.reason
        valurl, valuser, valpasw = False, False, False
        self.url, self.user, self.pasw = None, None, None
        if url == None or stat not in (200, 401):
            valurl = "Unable to access Nexus instance."
            valuser = "Unable to access Nexus instance."
            valpasw = "Unable to access Nexus instance."
        elif user == None or pasw == None or stat == 401:
            valurl = True
            valuser = "Incorrect username and/or password."
            valpasw = "Incorrect username and/or password."
            self.url = url
        else:
            valurl, valuser, valpasw = True, True, True
            self.url, self.user, self.pasw = url, user, pasw
        self.log.info("System ping completed, status: %s.", stat)
        return valurl, valuser, valpasw

    def dorequest(self, url, body, headers, method, oper, respq=False):
        try:
            req = MethodRequest(url, body, headers, method=method)
            if self.scr.sslnoverify:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                resp = urllib2.urlopen(req, context=ctx)
            else: resp = urllib2.urlopen(req)
            stat = resp.getcode()
        except urllib2.HTTPError as ex:
            msg = "Error connecting to Nexus:\n%s"
            self.log.exception(msg, ex.read())
            stat = ex.code
        except urllib2.URLError as ex:
            self.log.exception("Error connecting to Nexus:")
            stat = ex.reason
        self.log.info("%s responded with %s.", str(url), str(stat))
        if not isinstance(stat, (int, long)) or stat < 200 or stat >= 300:
            msg = "Unable to " + oper + " Nexus plugin: " + str(stat) + "."
            self.log.error(msg)
            return msg, None
        if respq == True: return None, json.load(resp)
        return None, None
