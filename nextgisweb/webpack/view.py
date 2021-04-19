# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals
import io
import os
import json
import os.path
import re
from shutil import copyfileobj
from tempfile import NamedTemporaryFile

from pyramid.response import FileResponse


def setup_pyramid(comp, config):
    comp.dist_path = comp.options['dist_path']
    webpack_dist = '/static{}/dist/*subpath'.format(comp.env.pyramid.static_key)
    config.add_route('webpack.dist', webpack_dist).add_view(dist)

    config.add_route('webpack.test', '/test/webpack') \
        .add_view(test, renderer="nextgisweb:webpack/template/test.mako")


def dist(request):
    dist_path = request.env.webpack.options['dist_path']
    subpath = request.matchdict['subpath']

    preproc = _preprocessed_filename(
        dist_path, '/'.join(subpath[:-1]),
        subpath[-1])
    return FileResponse(preproc, cache_max_age=3600, request=request)


def test(request):
    return dict()


def _preprocessed_filename(dist_path, file_dir, file_name):
    fullname = os.path.join(dist_path, file_dir, file_name)
    preproc = os.path.join(dist_path, file_dir, 'preproc-' + file_name)

    if not fullname.endswith('.js'):
        return fullname

    if os.path.exists(preproc):
        return preproc

    if not os.path.exists(fullname):
        return None

    entry_name = file_dir + '/' + file_name
    if entry_name.endswith('.js'):
        entry_name = entry_name[:-3]

    manifest = _load_manifest(dist_path)

    try:
        chunks = manifest['entrypoints'][entry_name]['assets']['js']
    except KeyError:
        chunks = None

    if chunks is None or len(chunks) <= 1:
        os.symlink(fullname.split('/')[-1], preproc)
        return preproc

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
            copyfileobj(src, tmp)

        # TODO: Cleanup temporary file when rename fails
        os.rename(tmp.name, preproc)
        return preproc


def _load_manifest(dist_path):
    # TODO: Add manifest file caching
    manifest_path = os.path.join(dist_path, 'assets-manifest.json')
    with io.open(manifest_path, 'r') as fd:
        manifest = json.load(fd)
        return manifest
