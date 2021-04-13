# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals
from uuid import uuid4
import six

import pytest
from osgeo import ogr

from nextgisweb.models import DBSession
from nextgisweb.auth import User
from nextgisweb.compat import Path
from nextgisweb.core.exception import ValidationError
from nextgisweb.resource.model import Resource
from nextgisweb.vector_layer import VectorLayer
from nextgisweb.spatial_ref_sys import SRS

path = Path(__file__).parent / 'data' / 'errors'


@pytest.mark.parametrize('data, skip_other_geometry_type, fix_errors, \
                          skip_errors, geometry_type, expect_error', (
    # ('geom-collection.geojson', False, 'NONE', False, None, True),
    # ('geom-collection.geojson', False, 'SAFE', False, None, False),

    # ('incomplete-geom.geojson', False, 'LOSSY', False, None, True),
    # ('incomplete-geom.geojson', False, 'LOSSY', True, None, False),

    # ('mixed-feature-geom.geojson', False, 'NONE', False, 'POINT', True),
    # ('mixed-feature-geom.geojson', False, 'NONE', True, 'POINT', False),
    # ('mixed-feature-geom.geojson', True, 'NONE', False, 'POINT', False),

    # ('no-features.geojson', False, 'NONE', False, None, True),
    # ('no-features.geojson', False, 'NONE', False, 'POINT', False),

    # ('non-multi-geom.geojson', False, 'NONE', False, None, False),

    ('null-geom.geojson', False, 'LOSSY', False, None, True),
    ('null-geom.geojson', False, 'LOSSY', True, None, False),
    ('null-geom.geojson', True, 'NONE', False, None, False),

    ('self-intersection.geojson', False, 'SAFE', False, None, True),
    ('self-intersection.geojson', False, 'LOSSY', False, None, False),

    ('single-geom-collection.geojson', False, 'NONE', False, 'POINT', True),
    ('single-geom-collection.geojson', False, 'SAFE', False, 'POINT', False),
    ('single-geom-collection.geojson', True, 'NONE', False, 'POINT', False),
    ('single-geom-collection.geojson', False, 'SAFE', False, 'LINESTRING', True),

    # ('unclosed-ring.geojson', False, 'LOSSY', False, None, True),
    # ('unclosed-ring.geojson', False, 'LOSSY', True, None, False),
))
def test_create_old(data, skip_other_geometry_type, fix_errors, skip_errors, geometry_type,
                expect_error, ngw_resource_group, ngw_txn):
    obj = VectorLayer(
        parent_id=ngw_resource_group, display_name='vector_layer',
        owner_user=User.by_keyname('administrator'),
        srs=SRS.filter_by(id=3857).one()
    )

    src = str(path / data)
    ds = ogr.Open(src)
    layer = ds.GetLayer(0)

    geom_cast_params = dict(
        geometry_type=geometry_type,
        is_multi=None,
        has_z=None)

    def fun():
        obj.setup_from_ogr(layer, skip_other_geometry_type=skip_other_geometry_type,
                           geom_cast_params=geom_cast_params)
        obj.load_from_ogr(layer, skip_other_geometry_type=skip_other_geometry_type,
                          fix_errors=fix_errors, skip_errors=skip_errors)

    if expect_error:
        with pytest.raises(ValidationError):
            fun()
    else:
        fun()


# List of creation test cases: file name, creation options, and final checks.
CREATE_TEST_PARAMS = (
    (
        'geom-collection.geojson', 
        dict(),
        dict(exception=ValidationError),
    ),

    (
        'geom-collection.geojson', 
        dict(fix_errors='SAFE'),
        dict(feature_count=2),
    ),

    (
        'incomplete-geom.geojson',
        dict(fix_errors='LOSSY'),
        dict(exception=ValidationError),
    ),

    (
        'incomplete-geom.geojson',
        dict(skip_errors=True),
        dict(feature_count=1)
    ),

    (
        'mixed-feature-geom.geojson',
        dict(geometry_type='POINT', skip_other_geometry_type=True),
        dict(geometry_type='MULTIPOINT', feature_count=2),
    ),
    (
        # The second MULTIPOINT geometry must be converted to a SINGLE geometry.
        # The first POINT should be taken in LOSSY mode.
        'mixed-feature-geom.geojson',
        dict(
            geometry_type='POINT', skip_other_geometry_type=True, 
            fix_errors='LOSSY', is_multi=False),
        dict(geometry_type='POINT', feature_count=2),
    ),
    (
        # The layer has only one LINESTRING geometry and it's valid.
        'mixed-feature-geom.geojson',
        dict(geometry_type='LINESTRING', skip_other_geometry_type=True),
        dict(geometry_type='LINESTRING', feature_count=1),
    ),

    (
        'non-multi-geom.geojson',
        dict(),
        dict(geometry_type='MULTIPOINT', feature_count=2),
    ),

    (
        # It's not possible to chose geometry type here.
        'empty.geojson',
        dict(),
        dict(exception=ValidationError),
    ),
    (
        # An empty layer with MULTIPOINTZ must be created.
        'empty.geojson',
        dict(geometry_type='POINT', is_multi=True, has_z=True),
        dict(geometry_type='MULTIPOINTZ', feature_count=0),
    ),

    (
        # The unclosed ring must be closed in SAFE mode, QGIS does it sielently.
        'unclosed-ring.geojson',
        dict(fix_errors='SAFE'),
        dict(feature_count=1),
    ),
)

@pytest.mark.parametrize('filename, options, checks', CREATE_TEST_PARAMS)
def test_create(filename, options, checks, ngw_resource_group, ngw_txn):
    obj = VectorLayer(
        parent_id=ngw_resource_group, display_name='vector_layer',
        owner_user=User.by_keyname('administrator'),
        srs=SRS.filter_by(id=3857).one(),
        tbl_uuid=six.text_type(uuid4().hex)
    ).persist()

    src = str(path / filename)
    ds = ogr.Open(src)
    layer = ds.GetLayer(0)

    geom_cast_params = dict(
        geometry_type=options.get('geometry_type'),
        is_multi=options.get('is_multi'),
        has_z=options.get('has_z'))

    def setup_and_load():
        setup_kwargs = dict()
        load_kwargs = dict()

        if 'skip_other_geometry_type' in options:
            setup_kwargs['skip_other_geometry_type'] = options['skip_other_geometry_type']
            load_kwargs['skip_other_geometry_type'] = options['skip_other_geometry_type']

        if 'fix_errors' in options:
            load_kwargs['fix_errors'] = options['fix_errors']
        if 'skip_errors' in options:
            load_kwargs['skip_errors'] = options['skip_errors']

        obj.setup_from_ogr(layer, geom_cast_params=geom_cast_params, **setup_kwargs)
        obj.load_from_ogr(layer, **load_kwargs)

    if 'exception' in checks:
        with pytest.raises(checks['exception']):
            setup_and_load()
        DBSession.expunge(obj)
    else:
        setup_and_load()
        
        DBSession.flush()
        
        if 'geometry_type' in checks:
            exp_geometry_type = checks['geometry_type']
            assert obj.geometry_type == exp_geometry_type, \
                "Expected geometry type was {} but actually got {}".format(
                    exp_geometry_type, obj.geometry_type)

        if 'feature_count' in checks:
            exp_feature_count = checks['feature_count']
            query = obj.feature_query()
            feature_count = query().total_count
            assert feature_count == exp_feature_count, \
                "Expected feature count was {} but got {}".format(
                    exp_feature_count, feature_count)


        