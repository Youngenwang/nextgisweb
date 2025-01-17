from time import sleep
from uuid import uuid4
import logging

import pytest
import transaction
from PIL import Image, ImageDraw
from shapely.geometry import Point

from nextgisweb.lib.geometry import Geometry
from nextgisweb.models import DBSession
from nextgisweb.vector_layer import VectorLayer
from nextgisweb.spatial_ref_sys import SRS
from nextgisweb.auth import User

from nextgisweb.render.model import ResourceTileCache
from nextgisweb.render.util import pack_color, unpack_color


@pytest.fixture
def frtc(ngw_resource_group):
    with transaction.manager:
        vector_layer = VectorLayer(
            parent_id=ngw_resource_group, display_name='from_fields',
            owner_user=User.by_keyname('administrator'),
            geometry_type='POINT',
            srs=SRS.filter_by(id=3857).one(),
            tbl_uuid=uuid4().hex
        ).persist()
        vector_layer.setup_from_fields([])

        result = ResourceTileCache(
            resource=vector_layer,
        ).persist()
        result.async_writing = True

        DBSession.flush()
        result.initialize()

    yield result

    with transaction.manager:
        DBSession.delete(ResourceTileCache.filter_by(resource_id=result.resource_id).one())
        DBSession.delete(VectorLayer.filter_by(id=vector_layer.id).one())


@pytest.fixture
def img_cross_red():
    result = Image.new('RGBA', (256, 256))
    draw = ImageDraw.Draw(result)
    draw.line((0, 0, 256, 256), fill='red')
    draw.line((0, 256, 256, 0), fill='red')
    return result


@pytest.fixture
def img_cross_green():
    result = Image.new('RGBA', (256, 256))
    draw = ImageDraw.Draw(result)
    draw.line((0, 0, 256, 256), fill='green')
    draw.line((0, 256, 256, 0), fill='green')
    return result


@pytest.fixture
def img_fill():
    result = Image.new('RGBA', (256, 256), (100, 100, 100, 100))
    return result


@pytest.fixture
def img_empty():
    result = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    return result


def test_pack_unpack():
    t = (255, 127, 63, 31)
    assert unpack_color(pack_color(t)) == t


def test_put_get_cross(frtc, img_cross_red):
    tile = (0, 0, 0)
    frtc.put_tile(tile, img_cross_red)
    exists, cimg = frtc.get_tile(tile)
    assert exists and cimg.getextrema() == img_cross_red.getextrema()


def test_put_get_fill(frtc, img_fill):
    tile = (0, 0, 0)
    frtc.put_tile(tile, img_fill)
    exists, cimg = frtc.get_tile(tile)
    assert exists and cimg.getextrema() == img_fill.getextrema()


def test_put_get_empty(frtc, img_empty):
    tile = (0, 0, 0)
    frtc.put_tile(tile, img_empty)
    exists, cimg = frtc.get_tile(tile)
    assert exists and cimg is None


def test_get_missing(frtc):
    tile = (0, 0, 0)
    exists, cimg = frtc.get_tile(tile)
    assert not exists


def test_ttl(frtc, img_cross_red):
    tile = (0, 0, 0)
    frtc.ttl = 1
    frtc.put_tile(tile, img_cross_red)
    sleep(1)
    exists, cimg = frtc.get_tile(tile)
    assert not exists


def test_clear(frtc, img_cross_red):
    tile = (0, 0, 0)
    frtc.put_tile(tile, img_cross_red)
    frtc.clear()
    exists, cimg = frtc.get_tile(tile)
    assert not exists


def test_invalidate(frtc, img_cross_red, img_cross_green, img_fill, caplog):
    caplog.set_level(logging.DEBUG)
    tile_invalid = (4, 0, 0)
    tile_valid = (4, 15, 15)

    frtc.put_tile(tile_invalid, img_cross_red)
    frtc.put_tile(tile_valid, img_cross_red)

    frtc.invalidate(Geometry.from_shape(Point(
        *frtc.resource.srs.tile_center(tile_invalid)),
        srid=None))

    exists, cimg = frtc.get_tile(tile_invalid)
    assert not exists

    exists, cimg = frtc.get_tile(tile_valid)
    assert exists and cimg.getextrema() == img_cross_red.getextrema()

    # Update previously invalidated tile
    frtc.put_tile(tile_invalid, img_cross_green)
    exists, cimg = frtc.get_tile(tile_invalid)
    assert exists and cimg.getextrema() == img_cross_green.getextrema()
