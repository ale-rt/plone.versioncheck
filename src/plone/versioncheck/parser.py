# -*- coding: utf-8 -*-

from collections import OrderedDict
from plone.versioncheck.utils import find_relative
from plone.versioncheck.utils import requests_session

import os.path
import sys

if sys.version_info < (3, 0):
    from ConfigParser import ConfigParser
    from ConfigParser import NoOptionError
    from ConfigParser import NoSectionError
    from StringIO import StringIO
elif sys.version_info >= (3, 0):
    from configparser import ConfigParser
    from configparser import NoOptionError
    from configparser import NoSectionError
    from io import StringIO


def _extract_versions_section(
    session,
    filename,
    version_sections=None,
    relative=None
):
    sys.stderr.write('\n- {0}'.format(filename))
    if (
        relative is not None and
        "://" not in filename and
        not filename.startswith('/') and
        not filename.startswith(relative)
    ):
        filename = relative + '/' + filename
    config = ConfigParser()
    if os.path.isfile(filename):
        config.read(filename)
    else:
        resp = session.get(filename)
        config.readfp(StringIO(resp.text))
        if resp.from_cache:
            sys.stderr.write('\n  from cache')
        elif resp.status_code != 200:
            sys.stderr.write('\n  ERROR {0:d}'.format(resp.status_code))
        else:
            sys.stderr.write('\n  fresh from server')
    # first read own versions section
    if config.has_section('versions'):
        version_sections[filename] = OrderedDict(config.items('versions'))
        sys.stderr.write(
            '\n  {0:d} entries in versions section.'.format(
                len(version_sections[filename])
            )
        )
    try:
        extends = config.get('buildout', 'extends').strip()
    except (NoSectionError, NoOptionError):
        return version_sections
    for extend in reversed(extends.splitlines()):
        extend = extend.strip()
        if not extend:
            continue
        sub_relative = find_relative(extend) or relative
        _extract_versions_section(
            session,
            extend,
            version_sections,
            sub_relative
        )
    return version_sections


def parse(buildout_filename, nocache=False):
    sys.stderr.write("Parsing buildout files:")
    if nocache:
        sys.stderr.write("\n(not using caches)")
    base_relative = find_relative(buildout_filename)
    session = requests_session(nocache=nocache)
    version_sections = _extract_versions_section(
        session,
        buildout_filename,
        version_sections=OrderedDict(),
        relative=base_relative
    )
    sys.stderr.write("\nparsing finished.\n")
    pkgs = {}

    for name in version_sections:
        for pkg in version_sections[name]:
            if pkg not in pkgs:
                pkgs[pkg] = OrderedDict()

    for pkgname in pkgs:
        pkg = pkgs[pkgname]
        for name in version_sections:
            if pkgname in version_sections[name]:
                pkg[name] = version_sections[name][pkgname]

    return pkgs
