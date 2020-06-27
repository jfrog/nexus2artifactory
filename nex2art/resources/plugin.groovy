import groovy.json.JsonBuilder
import org.sonatype.nexus.security.user.UserSearchCriteria
import org.apache.shiro.authz.permission.*

def getRepoData() {
    def repoman = container.lookup('org.sonatype.nexus.repository.manager.RepositoryManager')
    def repolist = []
    for (repo in repoman.browse()) {
        def repoitem = [:], configitem = [:]
        repoitem.type = repo.type.value
        repoitem.format = repo.format.value
        repoitem.name = repo.name
        repoitem.url = repo.url
        def config = repo.configuration
        configitem.name = config.repositoryName
        configitem.recipe = config.recipeName
        configitem.online = config.isOnline()
        configitem.attributes = config.attributes
        repoitem.config = configitem
        repolist << repoitem
    }
    return repolist
}

def getBlobstoreData() {
    def blobman = container.lookup('org.sonatype.nexus.blobstore.api.BlobStoreManager')
    def blobstorelist = []
    for (blobstore in blobman.browse()) {
        def blobstoreitem = [:]
        def config = blobstore.blobStoreConfiguration
        blobstoreitem.name = config.name
        blobstoreitem.type = config.type
        blobstoreitem.attributes = config.attributes
        blobstorelist << blobstoreitem
    }
    return blobstorelist
}

def getUserData() {
    def secsys = container.lookup('org.sonatype.nexus.security.SecuritySystem')
    def userlist = []
    for (user in secsys.searchUsers(new UserSearchCriteria())) {
        def useritem = [:], rolesitems = []
        useritem.id = user.userId
        useritem.firstname = user.firstName
        useritem.lastname = user.lastName
        useritem.email = user.emailAddress
        useritem.source = user.source
        for (role in user.roles) {
            def roleitem = [:]
            roleitem.id = role.roleId
            roleitem.source = role.source
            rolesitems << roleitem
        }
        useritem.roles = rolesitems
        useritem.status = user.status.name()
        useritem.readonly = user.isReadOnly()
        useritem.version = user.version
        userlist << useritem
    }
    return userlist
}

def getGroupData() {
    def secsys = container.lookup('org.sonatype.nexus.security.SecuritySystem')
    def grouplist = []
    for (group in secsys.listRoles()) {
        def groupitem = [:]
        groupitem.id = group.roleId
        groupitem.name = group.name
        groupitem.source = group.source
        groupitem.roles = group.roles
        groupitem.privileges = group.privileges
        groupitem.description = group.description
        groupitem.readonly = group.readOnly
        groupitem.version = group.version
        grouplist << groupitem
    }
    return grouplist
}

def getPermissionData() {
    def secsys = container.lookup('org.sonatype.nexus.security.SecuritySystem')
    def permlist = []
    for (perm in secsys.listPrivileges()) {
        def permitem = [:]
        permitem.id = perm.id
        permitem.name = perm.name
        permitem.description = perm.description
        permitem.type = perm.type
        permitem.properties = perm.properties
        permitem.readonly = perm.isReadOnly()
        permitem.version = perm.version
        permitem.perm = perm.permission.parts
        permlist << permitem
    }
    return permlist
}

def getSelectorData() {
    def selman = container.lookup('org.sonatype.nexus.selector.SelectorManager')
    def sellist = []
    if (selman == null) return sellist
    for (sel in selman.browse()) {
        def selitem = [:]
        selitem.name = sel.name
        selitem.type = sel.type
        selitem.description = sel.description
        selitem.attributes = sel.attributes
        sellist << selitem
    }
    return sellist
}

def getLdapData() {
    def confman = container.lookup('org.sonatype.nexus.ldap.persist.LdapConfigurationManager')
    def conflist = []
    for (conf in confman.listLdapServerConfigurations()) {
        def confitem = [:]
        confitem.id = conf.id
        confitem.name = conf.name
        confitem.order = conf.order
        confitem.searchBase = conf.connection.searchBase
        confitem.systemUsername = conf.connection.systemUsername
        confitem.systemPassword = conf.connection.systemPassword
        confitem.authScheme = conf.connection.authScheme
        confitem.useTrustStore = conf.connection.useTrustStore
        confitem.saslRealm = conf.connection.saslRealm
        confitem.connectionTimeout = conf.connection.connectionTimeout
        confitem.connectionRetryDelay = conf.connection.connectionRetryDelay
        confitem.maxIncidentsCount = conf.connection.maxIncidentsCount
        confitem.protocol = conf.connection.host.protocol.name()
        confitem.hostName = conf.connection.host.hostName
        confitem.port = conf.connection.host.port
        confitem.emailAddressAttribute = conf.mapping.emailAddressAttribute
        confitem.ldapGroupsAsRoles = conf.mapping.ldapGroupsAsRoles
        confitem.groupBaseDn = conf.mapping.groupBaseDn
        confitem.groupIdAttribute = conf.mapping.groupIdAttribute
        confitem.groupMemberAttribute = conf.mapping.groupMemberAttribute
        confitem.groupMemberFormat = conf.mapping.groupMemberFormat
        confitem.groupObjectClass = conf.mapping.groupObjectClass
        confitem.userPasswordAttribute = conf.mapping.userPasswordAttribute
        confitem.userIdAttribute = conf.mapping.userIdAttribute
        confitem.userObjectClass = conf.mapping.userObjectClass
        confitem.ldapFilter = conf.mapping.ldapFilter
        confitem.userBaseDn = conf.mapping.userBaseDn
        confitem.userRealNameAttribute = conf.mapping.userRealNameAttribute
        confitem.userSubtree = conf.mapping.userSubtree
        confitem.groupSubtree = conf.mapping.groupSubtree
        confitem.userMemberOfAttribute = conf.mapping.userMemberOfAttribute
        conflist << confitem
    }
    return conflist
}

def getData() {
    def data = [:]
    if (SKIPSEC) {
        data.users = []
        data.groups = []
        data.privs = []
        data.selectors = []
        data.ldaps = []
    } else {
        data.users = userData
        data.groups = groupData
        data.privs = permissionData
        data.selectors = selectorData
        data.ldaps = ldapData
    }
    data.repos = repoData
    data.blobstores = blobstoreData
    return new JsonBuilder(data).toPrettyString()
}

return data
