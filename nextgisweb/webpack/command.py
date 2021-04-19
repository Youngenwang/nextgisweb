# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals
import json
from collections import OrderedDict
from importlib import import_module
from subprocess import check_call

from ..compat import Path
from ..command import Command
from ..package import amd_packages


@Command.registry.register
class WebpackCommand(object):
    identity = 'webpack'
    no_initialize = True

    @classmethod
    def argparser_setup(cls, parser, env):
        pass

    @classmethod
    def execute(cls, args, env):
        client_packages = list()
        cwd = Path().resolve()
        for cid, cobj in env._components.items():
            cmod = import_module(cobj.__class__.__module__)
            cpath = Path(cmod.__file__).parent.resolve()
            jspkg = cpath / 'client'
            if jspkg.exists():
                client_packages.append(str(jspkg.relative_to(cwd)))
                if cid == 'webpack':
                    webpack_package = str(jspkg.relative_to(cwd))

        package_json = OrderedDict(private=True)
        package_json['config'] = config = OrderedDict()
        config['nextgisweb_webpack_root'] = str(Path().resolve())
        config['nextgisweb_webpack_packages'] = ','.join(client_packages)
        config['nextgisweb_webpack_external'] = ','.join([
            pname for pname, _ in amd_packages()])

        package_json['scripts'] = scripts = OrderedDict()
        webpack_config = '{}/webpack.config.cjs'.format(webpack_package)
        scripts['build'] = 'webpack --config {}'.format(webpack_config)
        scripts['watch'] = 'webpack --watch --config {}'.format(webpack_config)

        package_json['workspaces'] = client_packages

        with open('package.json', 'w') as fd:
            fd.write(json.dumps(package_json, indent=4))

        check_call(['yarn', 'install'])
