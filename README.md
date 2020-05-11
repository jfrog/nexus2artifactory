NexusToArtifactory
==================

This tool is designed to ease the transition from Sonatype Nexus to JFrog
Artifactory. It provides a simple wizard-like interface that allows you to
easily configure and run a migration of repositories, artifacts, users, and
settings from a Nexus instance to an Artifactory instance.

Currently, the following data can be migrated:
- local (hosted), remote (proxy), and virtual (group) repositories
  - note that Bower repositories are not yet supported
- artifacts stored in local (hosted) repositories
  - artifacts stored in remote caches are NOT currently migrated
- users, groups (roles), and permissions (privileges)
- LDAP configurations

Note that due to limitations in the REST API in Artifactory OSS, this tool can
only migrate to licensed Artifactory distributions (Pro, Enterprise, etc). It
does not work with free distributions (OSS, CE, etc).

Installation
------------

This tool accesses the Nexus instance directly by reading the Nexus files from
the disk. Therefore, the tool should be installed on the computer running the
Nexus instance, or on a computer with access to the filesystem that the Nexus
instance is installed on.

First, install the latest version of [Python 2][]. Then, [download][] or clone
this repository.

[Python 2]: https://www.python.org/downloads/
[download]: https://github.com/JFrogDev/nexus2artifactory/archive/master.zip

### Windows Installation ###

This tool's interface uses the `ncurses` library, which is standard in Linux and
MacOS, but not readily available in Windows. Instead, the tool can use the
`PDCurses` library as an alternative. This means that Windows users must also
have the latest version of [PDCurses][] to run the tool.

Alternatively, Windows users may avoid installing any dependencies by
downloading the self-contained [exe file][].

[PDCurses]: http://pdcurses.sourceforge.net/
[exe file]: https://github.com/JFrogDev/nexus2artifactory/raw/master/NexusToArtifactory.exe

Usage
-----

To run the tool, run `./NexusToArtifactory.py`.

If using the included Windows exe file, instead run `NexusToArtifactory.exe`.

![Main Menu Screenshot](doc/mainMenu.png)

All options can be accessed by typing the appropriate key on the keyboard. The
following options are available:
- <kbd>i</kbd> *Initial Setup* - Connect to the Nexus and Artifactory instances.
  This allows the tool to scan both, and come up with a default configuration
  for migration. This configuration can then be modified via the other options.
- <kbd>r</kbd> *Repository Migration Setup* - Allows you to specify which
  repositories should and should not be migrated. Also, allows you to modify any
  repository to some degree (changing the name, description, layout, etc). These
  changes only affect the current configuration, and will take effect on the
  Artifactory instance when the migration is run (the Nexus instance does not
  change).
- <kbd>u</kbd> *Security Migration Setup* - Migration options for security data,
  such as users, groups, permissions, and LDAP configurations.
- <kbd>s</kbd> *Save Config JSON File* - Allows you to save the current
  configuration to a JSON file. This way, you can close the tool and come back
  to it later, or you can save the current state of the migration to revert back
  to at a future time.
- <kbd>l</kbd> *Load Config JSON File* - Allows you to load a JSON file
  containing a configuration.
- <kbd>v</kbd> *Verify Configuration* - Rescan the Nexus and Artifactory
  instances, and reapply the current configuration. This should be used to check
  for incompatibilities after the Nexus instance has been modified.
- <kbd>x</kbd> *Run Migration* - Run the migration.
- <kbd>h</kbd> *Help* - Pressing another key after this one displays
  context-sensitive help for that option.
- <kbd>q</kbd> *Exit* - Quit the tool.

The first step is to connect to the Nexus and Artifactory instances, so type
<kbd>i</kbd> to open the Initial Setup menu.

![Setup Menu Screenshot](doc/setupMenu.png)

The following options are available:
- <kbd>n</kbd> *Nexus Data Directory* - The local filesystem path, where the Nexus
  instance is installed. This is generally a `sonatype-work/nexus/` folder. This
  path can be either a relative or absolute file path. If the path doesn't
  exist, or if it doesn't contain a valid Nexus install, this option will be
  hilighted in red.
- <kbd>a</kbd> *Artifactory URL* - The URL of the Artifactory instance. If the
  given URL is not a valid Artifactory instance, this option will be hilighted
  in red.
- <kbd>u</kbd> *Artifactory Username* - The username of an admin user on the
  given Artifactory instance.
- <kbd>p</kbd> *Artifactory Password* - The password of the admin user. Unless
  both the username and password are correct, they will both be hilighted in
  red.
- <kbd>h</kbd> *Help* - Pressing another key after this one displays
  context-sensitive help for that option.
- <kbd>q</kbd> *Back* - Go back to the main menu.

When a Nexus 3 path is specified, three new options will appear below it,
allowing you to input the Nexus URL, username, and password. This is because
Nexus 3 does not make all of its data available on the filesystem like Nexus 2
does, so the tool must connect to the instance to retrieve some of the
information.

![Setup Menu Screenshot With Filled Options](doc/setupFilled.png)

Once the Nexus and Artifactory instances have both been successfully connected,
type <kbd>q</kbd> to go back to the main menu.

![Main Menu Screenshot With Error](doc/mainErr.png)

* If you receive an error while connecting to Nexus, for 3.21.2 Nexus disabled the scripting related features for security reasons. This affects scripts as used through the Script REST API. This line should be added to $data-dir/etc/nexus.properties: ```nexus.scripts.allowCreation=true``` in order to resolve that and allow the API.

By this point, the tool has generated an initial configuration for the
migration, and all the settings have been set accordingly, but sometimes the
default settings need to be modified further. If there are any settings that
need to be changed, the corresponding option will be marked with a red `!`.
These must be cleared before running the migration.

In the screenshot above, there is an error in the Repository Migration Setup
menu, so type <kbd>r</kbd> to enter that menu.

![Repo Menu Screenshot With Error](doc/reposErr.png)

The following options are available:
- <kbd>1</kbd> *releases (maven)* - Typing a number key toggles whether to
  migrate the associated repository. The plus sign appears when the repository
  is to be migrated. This option also displays the package type, as well as
  whether the repository is a `(local)`, `[remote]`, `<shadow>`, or `{virtual}`.
  If there are a lot of repositories to show, they can be paged through using
  the left and right arrow keys.
- <kbd>f</kbd> *Search Filter* - Filter the repository list, displaying only
  repositories that match part of the filter string. This allows for easier
  browsing and editing of large lists of repositories.
- <kbd>m</kbd> *Mass Edit* - Allows editing of many repositories at once. Any
  fields set in the mass edit menu will overwrite existing values on all
  repositories that match the current search filter.
- <kbd>e</kbd> *Edit Repository* - Typing <kbd>e</kbd> followed by a number
  allows you to edit the associated repository.
- <kbd>h</kbd> *Help* - Pressing another key after this one displays
  context-sensitive help for that option.
- <kbd>q</kbd> *Back* - Go back to the main menu.

The error turns out to be in the `central-m1` repository, so type <kbd>e</kbd>
and then <kbd>6</kbd> to edit that one.

![Repo Edit Screenshot With Error](doc/repoErr.png)

The following options are available:
- *Repo Name (Nexus)* - The repository's name on the Nexus instance. Not
  editable.
- <kbd>n</kbd> *Repo Name (Artifactory)* - The repository's name on the
  Artifactory instance. Defaults to the Nexus repository name.
- <kbd>m</kbd> *Migrate This Repo* - Whether to migrate this repository. This is
  the same as typing the associated number in the repository list menu.
- *Repo Class* - Whether the repository is local, remote, shadow, or virtual.
  Not editable.
- *Repo Type* - The repository's package type. Not editable.
- <kbd>d</kbd> *Repo Description* - The repository description. Defaults to the
  "display name" of the repository on the Nexus instance.
- <kbd>l</kbd> *Repo Layout* - The layout of the repository. Defaults to the
  default layout for the repository's package type.
- <kbd>r</kbd> *Handles Releases* - Whether this repository handles releases.
  Local and remote repositories only.
- <kbd>s</kbd> *Handles Snapshots* - Whether this repository handles snapshots.
  Local and remote repositories only.
- <kbd>p</kbd> *Suppresses Pom Consistency Checks* - Whether this repository
  disables checking for inconsistencies with pom files before allowing artifacts
  to be deployed. Local and remote repositories only.
- <kbd>x</kbd> *Max Unique Snapshots* - The maximum number of unique snapshot
  versions. Local and remote repositories only.
- <kbd>b</kbd> *Maven Snapshot Version Behavior* - The behavior of snapshots in
  this repository. Local repositories only.
- <kbd>u</kbd> *Remote URL* - The URL of the repository this one proxies. Remote
  repositories only.
- <kbd>h</kbd> *Help* - Pressing another key after this one displays
  context-sensitive help for that option.
- <kbd>q</kbd> *Back* - Go back to the repository list menu.

The error shows that the repository's class, `shadow`, is invalid. There are a
handful of reasons that an initial configuration might not be valid:
- A Nexus repository, user, or role (group) has a name that would be invalid in
  Artifactory.
- A Nexus "shadow repository" is marked for migration. These cannot be migrated,
  as Artifactory does not have an equivalent concept.
- The `anonymous` user is marked for migration. This is a special user in
  Artifactory, and attempting to migrate it can break things.
- The default user password is not set. Passwords in Nexus are hashed, and so
  are impossible to migrate. The solution this tool uses is to set all user
  passwords to the same default password, and then expire all of them, so the
  user is forced to enter a new password when they first log in. This behavior
  can be overridden on a per-user basis by setting the `password` field for each
  user directly.
- A user marked as an administrator does not have the `password` field set. For
  security reasons, the tool will not allow an admin user to be set with an
  expired default password. All admin passwords must be entered manually.
- A user not marked as an administrator has administrator privileges. In Nexus,
  there are many special built-in privileges that allow access to various
  aspects of the Nexus system. All of these privileges fall into one of three
  categories:
  - The privilege allows access to something that doesn't exist in Artifactory.
  - The privilege allows access that all Artifactory users already have.
  - The privilege allows access that only Artifactory admins have.

  The former two types are ignored. If a user has the third type of privilege,
  they must also be marked as an administrator.

Since the `central-m1` repository is a shadow, it can't be migrated, so it must
be unmarked. Type <kbd>m</kbd> to unmark it, and then type <kbd>q</kbd> to go
back to the repository list. Alternatively, type <kbd>q</kbd> to go back to the
list, and then type <kbd>6</kbd> to unmark the repository.

![Repo Menu Screenshot](doc/repos.png)

Now, the error is gone. The error has disappeared on the main menu as well, and
the migration can now be run.

Search Filters
--------------

When viewing a very large list of items (repositories, users, groups, etc), it
can be helpful to only work on a subset of that list with certain properties,
search for a specific item, etc. The Search Filter key (<kbd>f</kbd>) can be
used to narrow down the list to only the items you want to see. This can make it
easier to find the items you want to modify. Alternatively, you can batch-update
all items that match the filter using the Mass Edit key (<kbd>m</kbd>).

The search filter is a string consisting of any number of space-separated terms.
The filter will match any item that matches all of those terms; it will filter
out all items that do not match at least one term. A term can be a part of an
item's name, or a `property=value` pair (not all properties are currently
supported, but will be eventually). For example, to view only hosted maven
repositories with a name containing "devel", the search filter would be:

```
devel class=local type=maven
```

The following term types are currently supported:

| Term            | Description                                               | Example        |
| --------------- | --------------------------------------------------------- | -------------- |
| `<text>`        | A matching item's name includes `<text>`.                 | `devel`        |
| `type=<type>`   | A matching repository's package type is `<type>`.         | `type=docker`  |
| `class=<class>` | A matching repository is `local`, `remote`, or `virtual`. | `class=remote` |

More property term types will be supported in the future. Other ways to combine
terms (OR and NOT operators, grouping, etc) will probably be supported in the
future.

Options
-------

This tool can optionally write logs to a file. This is primarily useful for
debugging purposes. Logging can be configured using the following commandline
options:
- `-l`, `--log-file`: Specify a file to write logs to. If the file already
  exists, the log session is appended to the existing contents. If this option
  is not given, no logging is performed.
- `-v`, `--log-level`: Specify the minimum log level. All logs below this level
  are ignored. Possible values are `error`, `warning`, `info`, and `debug`. If
  this option is not given, it defaults to `info`.

This tool can also be run programmatically, provided that a valid migration
configuration JSON has already been generated. This can be configured using the
following commandline options:
- `-f`, `--load-file`: Select a config JSON file to load immediately. This can
  be used in interactive mode, and is equivalent to using the <kbd>l</kbd>
  option on the tool's main screen. In non-interactive mode, this option is
  required.
- `-n`, `--non-interactive`: Run the tool in non-interactive mode. This loads
  the config JSON specified by `-f`, and immediately runs migration. If the
  config JSON was invalid or the migration had errors, the tool returns nonzero.
- `-q`, `--silent`: By default, non-interactive mode prints logs to stdout, as
  well as the file optionally specified by `-l`. If `-q` is passed, no logs are
  printed.

Other commandline options are as follows:
- `-r`, `--retries`: When migrating artifacts, a deploy might fail for some
  ephemeral reason (conflicts with in-progress metadata calculation, network
  issues, etc). This specifies the maximum number of times the tool will attempt
  to deploy each artifact before migration of that artifact fails. Default is 3.
- `-t`, `--threads`: The number of threads used to migrate artifacts. Default is
  4.
- `-s`, `--ssl-no-verify`: Disable SSL verification. This is useful if your
  Artifactory and/or Nexus 3 instance uses a self-signed SSL certificate.
- `-o`, `--force-tls10`: Forces TLSv1.0 to be used when HTTPS is used. Some
  SSL libraries have a bug that prevents them from properly using TLSv1.1 or
  later. If you have trouble connecting with HTTPS, try enabling this.
- `-h`, `--help`: Print help message, which describes all of these options.

Testing
-------

This project uses Python's [unittest framework][]. To run the tests, you can use
your favorite IDE, or run them from the command line.

To run the unit tests from the command line (requires Python 2.7):

``` shell
cd nex2art/tests
python -m unittest discover -v -p "*Test.py"
```

[unittest framework]: https://docs.python.org/2/library/unittest.html

Future Development
------------------

This tool is currently incomplete, and plenty of features are not yet
implemented. The following is a list of features that are currently in
development, and should be added to the tool soon:
- migrate Bower repositories
- migrate to Artifactory SaaS instances
- migrate scheduled tasks
- migrate other instance-wide settings (email settings, proxy settings, etc)
- support paid Nexus features, such as custom metadata
- modify virtual repository child lists
- modify repository package types

Nearly everything the tool does not yet migrate can be fixed manually via the
Artifactory user interface, after the migration is complete. A major exception
to this is if the tool chooses the wrong package type for a repository. If a
package type needs to be fixed after migration, [packageType.py][] might help.

[packageType.py]:
https://github.com/JFrogDev/artifactory-scripts/tree/master/4.x-migration
