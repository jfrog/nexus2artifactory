import os.path
import threading

class Maven(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.poms = []

    def deployPaths(self, localpath, metapath, repo, repopath):
        fname = os.path.basename(repopath)
        if fname == 'pom.xml' or fname.endswith('.pom'):
            pom = localpath, metapath, repo, repopath
            with self.lock:
                if pom not in self.poms:
                    self.poms.append(pom)
            return []
        return [(localpath, metapath, repo, repopath, {})]

    def cleanup(self):
        for localpath, metapath, repo, repopath in self.poms:
            yield localpath, metapath, repo, repopath, {}
