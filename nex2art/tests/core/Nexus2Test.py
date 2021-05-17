import unittest
import os, sys
import xml.etree.ElementTree as ET
# Allows easily running the tests without setting up python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from nex2art.core import Nexus2

class Nexus2Test(unittest.TestCase):
    def setUp(self):
        self.nexus = Nexus2(None)
        self.resourcesDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources', 'Nexus2Test')

    def tearDown(self):
        self.nexus = None

    # Test for Yum repo detection
    def test_getYumCapabilities(self):
        self.assertEqual(self.nexus.getYumCapabilities(
            os.path.join(self.resourcesDir, 'nonexistent.xml')), [])
        self.assertEqual(self.nexus.getYumCapabilities(
            os.path.join(self.resourcesDir, 'noYumRepoCapabilities.xml')), [])
        self.assertEqual(self.nexus.getYumCapabilities(
            os.path.join(self.resourcesDir, 'localYumRepoCapabilities.xml')), ['releases'])
        self.assertEqual(sorted(self.nexus.getYumCapabilities(
            os.path.join(self.resourcesDir, 'multipleYumRepoCapabilities.xml'))),
            sorted(['public', 'releases', 'central']))

    # Test for ability to pickup class (local, remote, virtual, shadow [not supported])
    def test_getRepoClass(self):
        # Local
        xml = ET.parse(os.path.join(self.resourcesDir, 'localRepo.xml'))
        result = {}
        self.nexus.getRepoClass(xml, result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result['class'], 'local')
        # Local URL
        xml = ET.parse(os.path.join(self.resourcesDir, 'localWithUrlRepo.xml'))
        result = {}
        self.nexus.getRepoClass(xml, result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result['class'], 'local')
        self.assertEqual(result['localurl'], '/Users/arturoa/paco/')
        # Remote
        xml = ET.parse(os.path.join(self.resourcesDir, 'remoteRepo.xml'))
        result = {}
        self.nexus.getRepoClass(xml, result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result['class'], 'remote')
        self.assertEqual(result['remote'], 'https://jcenter.bintray.com/')
        # Virtual
        xml = ET.parse(os.path.join(self.resourcesDir, 'virtualRepo.xml'))
        result = {}
        self.nexus.getRepoClass(xml, result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result['class'], 'virtual')
        self.assertEqual(sorted(result['repos']), sorted(['releases', 'snapshots', 'thirdparty', 'central']))
        # Shadow
        xml = ET.parse(os.path.join(self.resourcesDir, 'shadowRepo.xml'))
        result = {}
        self.nexus.getRepoClass(xml, result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result['class'], 'shadow')

    def test_getPackType(self):
        # Yum
        xml = ET.parse(os.path.join(self.resourcesDir, 'localWithUrlRepo.xml'))
        self.assertEqual(self.nexus.getPackType(['paco1'], xml), ('yum', 'simple-default'))
        # Generic
        xml = ET.parse(os.path.join(self.resourcesDir, 'genericRepo.xml'))
        self.assertEqual(self.nexus.getPackType([], xml), ('generic', 'simple-default'))
        # Maven 1
        xml = ET.parse(os.path.join(self.resourcesDir, 'localMaven1Repo.xml'))
        self.assertEqual(self.nexus.getPackType([], xml), ('maven', 'maven-1-default'))
        # Maven 2
        xml = ET.parse(os.path.join(self.resourcesDir, 'localRepo.xml'))
        self.assertEqual(self.nexus.getPackType([], xml), ('maven', 'maven-2-default'))
        # Gems
        xml = ET.parse(os.path.join(self.resourcesDir, 'remoteGemsRepo.xml'))
        self.assertEqual(self.nexus.getPackType([], xml), ('gems', 'simple-default'))
        # Nuget
        xml = ET.parse(os.path.join(self.resourcesDir, 'localNugetRepo.xml'))
        self.assertEqual(self.nexus.getPackType([], xml), ('nuget', 'nuget-default'))
        # NPM
        xml = ET.parse(os.path.join(self.resourcesDir, 'localNpmRepo.xml'))
        self.assertEqual(self.nexus.getPackType([], xml), ('npm', 'npm-default'))

if __name__ == '__main__':
    unittest.main()
