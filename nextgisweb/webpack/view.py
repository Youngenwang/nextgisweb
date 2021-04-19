# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals
import io
import re
import os
import json
import logging
import os.path
from shutil import copyfileobj, copystat
from tempfile import NamedTemporaryFile

from pyramid.response import FileResponse
from pyramid.httpexceptions import HTTPNotFound

_logger = logging.getLogger(__name__)


def setup_pyramid(comp, config):
    comp.dist_path = comp.options['dist_path']
    webpack_dist = '/static{}/dist/*subpath'.format(comp.env.pyramid.static_key)
    config.add_route('webpack.dist', webpack_dist).add_view(dist)

    config.add_route('webpack.test', '/test/webpack') \
        .add_view(test, renderer="nextgisweb:webpack/template/test.mako")
    config.add_route('webpack.vue', '/test/vue') \
        .add_view(test, renderer="nextgisweb:webpack/template/vue.mako")


def dist(request):
    dist_path = request.env.webpack.options['dist_path']
    subpath = request.matchdict['subpath']

    preproc = _preprocessed_filename(
        dist_path, '/'.join(subpath[:-1]),
        subpath[-1])

    if preproc is None:
        raise HTTPNotFound()

    return FileResponse(preproc, cache_max_age=3600, request=request)


def test(request):
    return dict()


def _preprocessed_filename(dist_path, file_dir, file_name):
    preproc_name = 'preproc-' + file_name
    fullname = os.path.join(dist_path, file_dir, file_name)
    preproc = os.path.join(dist_path, file_dir, preproc_name)

    if not fullname.endswith('.js'):
        if os.path.exists(fullname):
            return fullname
        else:
            return None

    if os.path.exists(preproc):
        stat_fullname = os.stat(fullname)
        stat_preproc = os.stat(preproc)
        if abs(stat_preproc.st_mtime - stat_fullname.st_mtime) < 1e-3:
            return preproc
        else:
            _logger.debug("File [{}/{}] is changed! Recreating...".format(file_dir, file_name))

    if not os.path.exists(fullname):
        return None

    entry_name = file_dir + '/' + file_name
    if entry_name.endswith('.js'):
        entry_name = entry_name[:-3]

    manifest = _load_manifest(dist_path)

    try:
        chunks = manifest['entrypoints'][entry_name]['assets']['js']
    except KeyError:
        chunks = []

    _logger.debug("Creating preprocessed copy of [{}/{}]".format(file_dir, file_name))
    with NamedTemporaryFile(dir=dist_path, delete=False) as tmp:
        with open(fullname, 'r') as src:
            line = src.read(512)
            m = re.match(r'define\((?:(\[[^\]]*\]),)?\s*\(', line)
            if m is not None:
                existing = m.group(1)
                deps = json.loads(existing) if existing else []
                deps.extend([('dist/' + c[:-3]) for c in chunks[:-1]])
                tmp.write("define({}, (".format(json.dumps(deps)) + line[
                    len(m.group(0)):])
            else:
                tmp.write(line)
            copyfileobj(src, tmp)

        # TODO: Cleanup temporary file when rename fails
        os.rename(tmp.name, preproc)

    copystat(fullname, preproc)
    return preproc


def _load_manifest(dist_path):
    # TODO: Add manifest file caching
    manifest_path = os.path.join(dist_path, 'assets-manifest.json')
    with io.open(manifest_path, 'r') as fd:
        manifest = json.load(fd)
        return manifest
