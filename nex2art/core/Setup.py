import sys
import ssl
import logging
import argparse
from functools import wraps

# Windows seems to have an issue with writing some logs to curses window if
# there are no handlers specified. This handler does nothing, but it prevents
# that issue.
class NilHandler(logging.Handler):
    def handle(self, record):
        pass

    def emit(self, record):
        pass

    def createLock(self):
        self.lock = None

class Dots(object):
    def __str__(self):
        return '...'

    def __repr__(self):
        return '...'

class PosIntFilter(object):
    def __contains__(self, item):
        return isinstance(item, int) and item > 0

    def __iter__(self):
        yield 1
        yield 2
        yield Dots()

class Setup(object):
    def __init__(self, argssource):
        self.argssource = argssource
        self.args = self.getargs()
        if self.args.force_tls10: self.fixssl()
        self.startlogging(self.args)

    # Some versions of SSL have a bug that causes an exception to be thrown when
    # a connection is made using TLSv1.1/TLSv1.2. This hack works around this
    # problem by forcing TLSv1.0.
    def fixssl(self):
        def sslwrap(func):
            @wraps(func)
            def bar(*args, **kw):
                kw['ssl_version'] = ssl.PROTOCOL_TLSv1
                return func(*args, **kw)
            return bar
        ssl.wrap_socket = sslwrap(ssl.wrap_socket)

    def startlogging(self, args):
        logfile = args.log_file
        noninteractive = args.non_interactive and not args.silent
        if logfile == None and not noninteractive:
            logging.getLogger().addHandler(NilHandler())
            return
        level = logging.INFO
        if args.log_level == 'error': level = logging.ERROR
        elif args.log_level == 'warning': level = logging.WARNING
        elif args.log_level == 'debug': level = logging.DEBUG
        fmt = "%(asctime)s [%(threadName)s] [%(levelname)s]"
        fmt += " (%(name)s:%(lineno)d) - %(message)s"
        formatter = logging.Formatter(fmt)
        logger = logging.getLogger()
        logger.setLevel(level)
        if logfile != None:
            fileh = logging.FileHandler(logfile)
            fileh.setFormatter(formatter)
            logger.addHandler(fileh)
        if noninteractive:
            stdouth = logging.StreamHandler(sys.stdout)
            stdouth.setFormatter(formatter)
            logger.addHandler(stdouth)
        msg = "\n\nNexus To Artifactory Migration Tool\n\n"
        logger.critical('\n' + '='*60 + msg + '='*60 + '\n')

    def getargs(self):
        help = [
            "Migrate Sonatype Nexus instances to JFrog Artifactory.",
            "the file to use for logging (default: don't write logs)",
            "the threshold to use for the logging level, if logs are written",
            "whether to disable ssl verification (e.g. for self-signed certs)",
            "whether to force TLSv1.0 (circumvents a bug with TLSv1.1/1.2 in some SSL libaries)",
            "the configuration file to load automatically on start",
            "migrate immediately without displaying the UI (requires -f)",
            "suppress logging to the console in non-interactive mode",
            "maximum number of attempts to upload each artifact before failure",
            "number of threads to use when migrating artifacts",
            "disable migration of users, groups, and permissions"]
        chcs = 'error', 'warning', 'info', 'debug'
        filt = PosIntFilter()
        parser = argparse.ArgumentParser(description=help[0])
        parser.add_argument('-l', '--log-file', help=help[1])
        parser.add_argument('-v', '--log-level', choices=chcs,
                            default='info', help=help[2])
        parser.add_argument('-s', '--ssl-no-verify',
                            action='store_true', help=help[3])
        parser.add_argument('-o', '--force-tls10',
                            action='store_true', help=help[4])
        parser.add_argument('-f', '--load-file', help=help[5])
        parser.add_argument('-n', '--non-interactive',
                            action='store_true', help=help[6])
        parser.add_argument('-q', '--silent', action='store_true', help=help[7])
        parser.add_argument('-r', '--retries', type=int, choices=filt,
                            default=3, help=help[8])
        parser.add_argument('-t', '--threads', type=int, choices=filt,
                            default=4, help=help[9])
        parser.add_argument('-d', '--disable-security-migration',
                            action='store_true', help=help[10])
        args = parser.parse_args(self.argssource)
        if args.load_file == None and args.non_interactive:
            parser.error("option --load-file is required for non-interactive mode")
        return args
