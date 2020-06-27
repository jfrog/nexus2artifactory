import os
import logging
import xml.etree.ElementTree as ET
from . import Security2, Ldap2

class Nexus2(object):
    def __init__(self, scr):
        self.scr = scr
        self.log = logging.getLogger(__name__)
        self.path = None
        self.repos = None
        self.repomap = None
        self.ldap = Ldap2()
        self.security = Security2()

    def refresh(self, path):
        repos, repomap, targs = [], {}, {}
        self.path = None
        self.repos = None
        self.repomap = None
        self.ldap.initialize()
        self.security.initialize()
        if path == None: return True
        path = os.path.abspath(path)
        xmlcap = os.path.join(path, 'conf', 'capabilities.xml')
        caps = self.getYumCapabilities(xmlcap)
        config = os.path.join(path, 'conf', 'nexus.xml')
        self.log.info("Reading Nexus config from %s.", config)
        if not os.path.isfile(config):
            self.log.error("Nexus config file does not exist.")
            return "Given path is not a valid Nexus instance."
        try:
            xml = ET.parse(config).getroot()
            targs = self.security.gettargets(xml)
            xmlrepos = xml.find('repositories')
            if xmlrepos == None: xmlrepos = []
            else: xmlrepos = xmlrepos.findall('repository')
            for repo in xmlrepos:
                repodata = {}
                repodata['id'] = repo.find('id').text
                repodata['desc'] = repo.find('name').text
                typ, layout = self.getPackType(caps, repo)
                repodata['type'] = typ
                repodata['layout'] = layout
                self.getRepoClass(repo, repodata)
                ext = repo.find('externalConfiguration')
                policy = None
                if ext != None: policy = ext.find('repositoryPolicy')
                repodata['release'] = False
                repodata['snapshot'] = False
                repodata['behavior'] = 'unique'
                repodata['maxuniquesnapshots'] = None
                if policy != None:
                    repodata['release'] = policy.text in ('RELEASE', 'MIXED')
                    repodata['snapshot'] = policy.text in ('SNAPSHOT', 'MIXED')
                repos.append(repodata)
                repomap[repodata['id']] = repodata
            self.log.info("Successfully read Nexus config.")
        except:
            self.log.exception("Error reading Nexus config:")
            return "Configuration file nexus.xml is not valid."
        repos.sort(key=lambda x: x['class'])
        if not self.scr.args.disable_security_migration:
            self.ldap.refresh(path)
            secrtn = self.security.refresh(path, targs, repos)
            if secrtn != True: return secrtn
        self.repos = repos
        self.repomap = repomap
        self.path = path
        return True

    def getRepoClass(self, repo, repodata):
        ext = repo.find('externalConfiguration')
        members, master = None, None
        if ext != None:
            members = ext.find('memberRepositories')
            master = ext.find('masterRepositoryId')
        remote = repo.find('remoteStorage')
        local = repo.find('localStorage')
        if local != None:
            localurl = local.find('url')
            if localurl != None:
                lurl = localurl.text
                if lurl[-1] != '/': lurl += '/'
                repodata['localurl'] = lurl
        if members != None:
            repodata['class'] = 'virtual'
            repodata['repos'] = []
            for child in members.findall('memberRepository'):
                repodata['repos'].append(child.text)
        elif remote != None:
            repodata['class'] = 'remote'
            repodata['remote'] = remote.find('url').text
        elif master != None: repodata['class'] = 'shadow'
        else: repodata['class'] = 'local'

    def getPackType(self, caps, repo):
        if repo.find('id').text in caps: return 'yum', 'simple-default'
        rtypes = ['maven1', 'maven2', 'npm', 'nuget', 'gems']
        ltypes = ['bower', 'gradle', 'ivy', 'npm', 'nuget', 'sbt', 'vcs']
        hint = repo.find('providerHint').text
        if hint == None: return 'generic', 'simple-default'
        subs = hint[hint.rfind('-'):]
        if subs in ('-shadow', '-hosted', '-proxy', '-group'):
            hint = hint[:hint.rfind('-')]
        if hint == 'm2-m1': hint = 'maven1'
        elif hint == 'm1-m2': hint = 'maven2'
        elif hint == 'rubygems': hint = 'gems'
        if hint not in rtypes: hint = 'generic'
        layout = 'simple'
        if hint in ltypes: layout = hint
        elif hint == 'maven1': hint, layout = 'maven', 'maven-1'
        elif hint == 'maven2': hint, layout = 'maven', 'maven-2'
        return hint, layout + '-default'

    def getYumCapabilities(self, xml):
        if not os.path.isfile(xml): return []
        root = ET.parse(xml).getroot()
        caps = root.find('capabilities')
        if caps == None: return []
        yumrepos = []
        for cap in caps.findall('capability'):
            tid = cap.find('typeId').text
            if tid not in ('yum.generate', 'yum.proxy', 'yum.merge'): continue
            props = {}
            xmlprops = cap.find('properties')
            if xmlprops == None: xmlprops = []
            else: xmlprops = xmlprops.findall('property')
            for prop in xmlprops:
                props[prop.find('key').text] = prop.find('value').text
            yumrepos.append(props['repository'])
        return yumrepos

    def checkNexus(self):
        nx = self.scr.nexus
        nx.vurl, nx.vuser, nx.vpasw = True, True, True
        newpath = self.scr.state["Initial Setup"]["Nexus Data Directory"].data
        nx.vpath = self.refresh(newpath)
        self.scr.format.update()
