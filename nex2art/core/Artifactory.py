import os
import re
import sys
import json
import base64
import logging
import urllib
import urllib2
import urlparse
import StringIO
import subprocess
import xml.etree.ElementTree as ET
from . import Upload

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

class MigrationError(Exception):
    def __init__(self, value):
        self.value = value

class Artifactory:
    def __init__(self, scr):
        self.log = logging.getLogger(__name__)
        self.scr = scr
        self.upload = Upload(scr, self)
        self.json = re.compile(r'^application/(?:[^;]+\+)?json(?:;.+)?$')
        self.xml = re.compile(r'^application/(?:[^;]+\+)?xml(?:;.+)?$')
        self.url = None
        self.user = None
        self.pasw = None

    def migrate(self, prog, conf):
        try:
            if None in (self.url, self.user, self.pasw):
                msg = "Connection to Artifactory server not configured."
                raise MigrationError(msg)
            self.log.info("Migrating to Artifactory.")
            self.prog = prog
            secconf = conf["Security Migration Setup"]
            self.initprogress(conf, secconf)
            cfg = "api/system/configuration"
            conn = self.setupconn()
            self.log.info("Enabling password expiration.")
            artxml = self.dorequest(conn, 'GET', cfg)
            root = artxml.getroot()
            ns = root.tag[:root.tag.index('}') + 1]
            pexpire = self.enablePasswordExpire(root, ns)
            self.dorequest(conn, 'POST', cfg, artxml)
            self.prog.refresh()
            self.migraterepos(conn, conf)
            self.migrategroups(conn, secconf)
            self.migrateusers(conn, secconf)
            self.migrateperms(conn, secconf)
            self.log.info("Resetting password expiration.")
            artxml = self.dorequest(conn, 'GET', cfg)
            root = artxml.getroot()
            ns = root.tag[:root.tag.index('}') + 1]
            self.migrateldap(conf, root, ns)
            self.disablePasswordExpire(root, ns, pexpire)
            self.dorequest(conn, 'POST', cfg, artxml)
            self.upload.upload(conf)
            return True
        except MigrationError as ex:
            self.log.exception("Migration Error:")
            return ex.value

    def enablePasswordExpire(self, root, ns):
        exp, itr = None, None
        try: itr = root.iter(ns + 'expirationPolicy')
        except AttributeError: itr = root.getiterator(ns + 'expirationPolicy')
        for pol in itr: exp = pol
        enabled = exp.find(ns + 'enabled')
        cfg, enabled.text = enabled.text, 'true'
        return cfg

    def disablePasswordExpire(self, root, ns, cfg):
        exp, itr = None, None
        try: itr = root.iter(ns + 'expirationPolicy')
        except AttributeError: itr = root.getiterator(ns + 'expirationPolicy')
        for pol in itr: exp = pol
        enabled = exp.find(ns + 'enabled')
        enabled.text = cfg

    def initprogress(self, conf, secconf):
        repoct, grpct, usrct, permct, confct = 0, 0, 0, 0, 0
        if "Repository Migration Setup" in conf:
            for repn, rep in conf["Repository Migration Setup"].items():
                if rep['available'] != True: continue
                if rep["Migrate This Repo"] != True: continue
                repoct += 1
        if "Groups Migration Setup" in secconf:
            for grpn, grp in secconf['Groups Migration Setup'].items():
                if grp['available'] != True: continue
                if grp["Migrate This Group"] != True: continue
                grpct += 1
        if "Users Migration Setup" in secconf:
            for usern, user in secconf['Users Migration Setup'].items():
                if not isinstance(user, dict): continue
                if user['available'] != True: continue
                if user["Migrate This User"] != True: continue
                usrct += 1
        if "Permissions Migration Setup" in secconf:
            for permn, perm in secconf['Permissions Migration Setup'].items():
                if perm['available'] != True: continue
                if perm["Migrate This Permission"] != True: continue
                permct += 1
        ldapq = True
        if "LDAP Migration Setup" not in conf["Security Migration Setup"]:
            ldapq = False
        else:
            src = conf["Security Migration Setup"]["LDAP Migration Setup"]
            if src["Migrate LDAP"] == False: ldapq = False
        if ldapq: confct += 1
        self.prog.stepsmap['Repositories'][2] = repoct
        self.prog.stepsmap['Groups'][2] = grpct
        self.prog.stepsmap['Users'][2] = usrct
        self.prog.stepsmap['Permissions'][2] = permct
        self.prog.stepsmap['Configurations'][2] = confct
        self.prog.stepsmap['Artifacts'][2] = 1
        self.prog.refresh()

    def migraterepos(self, conn, conf):
        self.log.info("Migrating repository definitions.")
        cfg = 'api/repositories'
        result = self.dorequest(conn, 'GET', cfg)
        nrepos = {}
        for nrepo in self.scr.nexus.repos: nrepos[nrepo['id']] = nrepo
        repos = {}
        for res in result: repos[res['key']] = True
        for repn, rep in conf["Repository Migration Setup"].items():
            if rep['available'] != True: continue
            if rep["Migrate This Repo"] != True: continue
            self.log.info("Migrating repo %s -> %s.", repn,
                          rep["Repo Name (Artifactory)"])
            self.prog.current = repn + ' -> ' + rep["Repo Name (Artifactory)"]
            self.prog.refresh()
            try:
                nrepo = nrepos[repn]
                jsn = {}
                jsn['key'] = rep["Repo Name (Artifactory)"]
                jsn['rclass'] = nrepo['class']
                jsn['packageType'] = nrepo['type']
                jsn['description'] = rep["Repo Description"]
                jsn['repoLayoutRef'] = rep["Repo Layout"]
                if jsn['rclass'] == 'local':
                    jsn['handleReleases'] = rep["Handles Releases"]
                    jsn['handleSnapshots'] = rep["Handles Snapshots"]
                if jsn['rclass'] == 'remote':
                    jsn['handleReleases'] = rep["Handles Releases"]
                    jsn['handleSnapshots'] = rep["Handles Snapshots"]
                    jsn['url'] = rep["Remote URL"]
                if jsn['rclass'] == 'virtual':
                    jsn['repositories'] = nrepo['repos']
                mthd = 'POST' if jsn['key'] in repos else 'PUT'
                cfg = 'api/repositories/' + urllib.quote(jsn['key'], '')
                self.dorequest(conn, mthd, cfg, jsn)
            except:
                self.log.exception("Error migrating repository %s:", repn)
                self.prog.stepsmap['Repositories'][3] += 1
            finally: self.prog.stepsmap['Repositories'][1] += 1

    def migrateusers(self, conn, conf):
        self.log.info("Migrating users.")
        passresets = []
        cfg = 'api/security/users'
        result = self.dorequest(conn, 'GET', cfg)
        usrs = {}
        for res in result: usrs[res['name']] = True
        if 'Users Migration Setup' not in conf: return
        defaultpasw = conf['Users Migration Setup']["Default Password"]
        for usern, user in conf['Users Migration Setup'].items():
            if not isinstance(user, dict): continue
            if user['available'] != True: continue
            if user["Migrate This User"] != True: continue
            self.log.info("Migrating user %s -> %s.", usern,
                          user["User Name (Artifactory)"])
            self.prog.current = usern + ' -> ' + user["User Name (Artifactory)"]
            self.prog.refresh()
            try:
                jsn = {}
                jsn['name'] = user["User Name (Artifactory)"]
                jsn['email'] = user["Email Address"]
                if "Password" in user:
                    jsn['password'] = user["Password"]
                else:
                    jsn['password'] = defaultpasw
                    passresets.append(jsn['name'].lower())
                jsn['admin'] = user["Is An Administrator"]
                jsn['groups'] = []
                for group in user["Groups"]:
                    if group in self.scr.nexus.security.roles:
                        try:
                            grp = conf["Groups Migration Setup"][group]
                            group = grp["Group Name (Artifactory)"]
                        except: pass
                        jsn['groups'].append(group)
                mthd = 'POST' if jsn['name'] in usrs else 'PUT'
                cfg = 'api/security/users/' + urllib.quote(jsn['name'], '')
                self.dorequest(conn, mthd, cfg, jsn)
            except:
                self.log.exception("Error migrating user %s:", usern)
                self.prog.stepsmap['Users'][3] += 1
            finally: self.prog.stepsmap['Users'][1] += 1
        if len(passresets) > 0:
            cfg = 'api/security/users/authorization/expirePassword'
            self.dorequest(conn, 'POST', cfg, passresets)

    def migrategroups(self, conn, conf):
        self.log.info("Migrating groups.")
        cfg = 'api/security/groups'
        result = self.dorequest(conn, 'GET', cfg)
        grps = {}
        for res in result: grps[res['name']] = True
        if 'Groups Migration Setup' not in conf: return
        for grpn, grp in conf['Groups Migration Setup'].items():
            if grp['available'] != True: continue
            if grp["Migrate This Group"] != True: continue
            self.log.info("Migrating group %s -> %s.", grpn,
                          grp["Group Name (Artifactory)"])
            self.prog.current = grpn + ' -> ' + grp["Group Name (Artifactory)"]
            self.prog.refresh()
            try:
                jsn = {}
                jsn['name'] = grp["Group Name (Artifactory)"]
                jsn['description'] = grp["Group Description"]
                jsn['autoJoin'] = grp["Auto Join Users"]
                mthd = 'POST' if jsn['name'] in grps else 'PUT'
                cfg = 'api/security/groups/' + urllib.quote(jsn['name'], '')
                self.dorequest(conn, mthd, cfg, jsn)
            except:
                self.log.exception("Error migrating group %s:", grpn)
                self.prog.stepsmap['Groups'][3] += 1
            finally: self.prog.stepsmap['Groups'][1] += 1

    def migrateperms(self, conn, conf):
        self.log.info("Migrating permissions.")
        cfg = 'api/security/permissions'
        result = self.dorequest(conn, 'GET', cfg)
        grpdata = {}
        if 'Groups Migration Setup' not in conf:
            conf['Groups Migration Setup'] = {}
        for grpn, grp in conf['Groups Migration Setup'].items():
            grpname = grp["Group Name (Artifactory)"]
            if 'Permissions' not in grp: continue
            for permn, perm in grp['Permissions'].items():
                perms = list(perm)
                if permn in grpdata: grpdata[permn][grpname] = perms
                else: grpdata[permn] = {grpname: perms}
        privs = self.scr.nexus.security.privs
        if 'Permissions Migration Setup' not in conf: return
        for permn, perm in conf['Permissions Migration Setup'].items():
            if perm['available'] != True: continue
            if perm["Migrate This Permission"] != True: continue
            self.log.info("Migrating permission %s -> %s.", permn,
                          perm["Permission Name (Artifactory)"])
            self.prog.current = permn + ' -> '
            self.prog.current += perm["Permission Name (Artifactory)"]
            self.prog.refresh()
            try:
                name = perm["Permission Name (Artifactory)"]
                incpat = ','.join(perm["Include Patterns"])
                excpat = ','.join(perm["Exclude Patterns"])
                repo = privs[name]['repo']
                if repo == '*': repo = 'ANY'
                grps = grpdata[name] if name in grpdata else {}
                jsn = {}
                jsn['name'] = name
                jsn['includesPattern'] = incpat
                jsn['excludesPattern'] = excpat
                jsn['repositories'] = [repo]
                jsn['principals'] = {'users': {}, 'groups': grps}
                cfg = 'api/security/permissions/' + urllib.quote(jsn['name'], '')
                self.dorequest(conn, 'PUT', cfg, jsn)
            except:
                self.log.exception("Error migrating permission %s:", permn)
                self.prog.stepsmap['Permissions'][3] += 1
            finally: self.prog.stepsmap['Permissions'][1] += 1

    def migrateldap(self, conf, root, ns):
        if "LDAP Migration Setup" not in conf["Security Migration Setup"]:
            return
        src = conf["Security Migration Setup"]["LDAP Migration Setup"]
        if src["Migrate LDAP"] == False: return
        self.log.info("Migrating LDAP configuration.")
        self.prog.current = "LDAP"
        self.prog.refresh()
        try:
            data = self.scr.nexus.ldap.ldap
            itr = None
            ldap = self.buildldap(ns)
            try: itr = ldap.iter()
            except AttributeError: itr = ldap.getiterator()
            for item in itr:
                tag = item.tag
                if item.tag.startswith(ns): tag = item.tag[len(ns):]
                if tag == 'key': item.text = src["LDAP Setting Name"]
                elif tag == 'name': item.text = src["LDAP Group Name"]
                elif tag == 'enabledLdap': item.text = src["LDAP Setting Name"]
                elif tag == 'managerPassword' and 'managerDn' in data:
                    item.text = src["LDAP Password"]
                elif tag in data: item.text = data[tag]
            sec = root.find(ns + 'security')
            sets = sec.find(ns + 'ldapSettings')
            newset = ldap.find(ns + 'ldapSetting')
            ldap.remove(newset)
            key = newset.find(ns + 'key').text
            for grp in sets.findall(ns + 'ldapSetting'):
                if grp.find(ns + 'key').text == key: sets.remove(grp)
            sets.append(newset)
            if 'strategy' not in data: return
            grps = sec.find(ns + 'ldapGroupSettings')
            newgrp = ldap.find(ns + 'ldapGroupSetting')
            ldap.remove(newgrp)
            name = newgrp.find(ns + 'name').text
            for grp in grps.findall(ns + 'ldapGroupSetting'):
                if grp.find(ns + 'name').text == name: grps.remove(grp)
            grps.append(newgrp)
        except:
            self.log.exception("Error migrating LDAP configuration:")
            self.prog.stepsmap['Configurations'][3] += 1
        finally: self.prog.stepsmap['Configurations'][1] += 1
        self.prog.refresh()

    def buildldap(self, ns):
        ldap = ET.Element('ldap')
        lset = ET.SubElement(ldap, ns + 'ldapSetting')
        ET.SubElement(lset, ns + 'key')
        ET.SubElement(lset, ns + 'enabled').text = 'true'
        ET.SubElement(lset, ns + 'ldapUrl')
        srch = ET.SubElement(lset, ns + 'search')
        ET.SubElement(srch, ns + 'searchFilter')
        ET.SubElement(srch, ns + 'searchBase')
        ET.SubElement(srch, ns + 'searchSubTree')
        ET.SubElement(srch, ns + 'managerDn')
        ET.SubElement(srch, ns + 'managerPassword')
        ET.SubElement(lset, ns + 'autoCreateUser').text = 'false'
        ET.SubElement(lset, ns + 'emailAttribute')
        lgrp = ET.SubElement(ldap, ns + 'ldapGroupSetting')
        ET.SubElement(lgrp, ns + 'name')
        ET.SubElement(lgrp, ns + 'groupBaseDn')
        ET.SubElement(lgrp, ns + 'groupNameAttribute')
        ET.SubElement(lgrp, ns + 'groupMemberAttribute')
        ET.SubElement(lgrp, ns + 'subTree')
        ET.SubElement(lgrp, ns + 'filter')
        ET.SubElement(lgrp, ns + 'descriptionAttribute').text = 'description'
        ET.SubElement(lgrp, ns + 'strategy')
        ET.SubElement(lgrp, ns + 'enabledLdap')
        return ldap

    def setupconn(self):
        headers = {'User-Agent': 'nex2art'}
        enc = base64.b64encode(self.user + ':' + self.pasw)
        headers['Authorization'] = "Basic " + enc
        return self.url[0], self.url[1], self.url[2], headers

    def dorequest(self, conndata, method, path, body=None):
        resp, stat, msg, ctype = None, None, None, None
        headers = {}
        if isinstance(body, (dict, list, tuple)):
            body = json.dumps(body)
            headers['Content-Type'] = 'application/json'
        elif isinstance(body, ET.ElementTree):
            fobj = StringIO.StringIO()
            body.write(fobj)
            body = fobj.getvalue()
            fobj.close()
            headers['Content-Type'] = 'application/xml'
        scheme, host, rootpath, extraheaders = conndata
        headers.update(extraheaders)
        url = urlparse.urlunsplit((scheme, host, rootpath + path, '', ''))
        req = MethodRequest(url, body, headers, method=method)
        self.log.info("Sending %s request to %s.", method, url)
        try:
            resp = urllib2.urlopen(req)
            stat = resp.getcode()
            ctype = resp.info().get('Content-Type', 'application/octet-stream')
        except urllib2.HTTPError as ex:
            self.log.exception("Error making request:")
            stat = ex.code
        except urllib2.URLError as ex:
            self.log.exception("Error making request:")
            stat = ex.reason
        if not isinstance(stat, (int, long)) or stat < 200 or stat >= 300:
            msg = "Unable to " + method + " " + path + ": " + str(stat) + "."
            raise MigrationError(msg)
        try:
            if self.json.match(ctype) != None: msg = json.load(resp)
            elif self.xml.match(ctype) != None: msg = ET.parse(resp)
            else: msg = resp.read()
        except: pass
        return msg
