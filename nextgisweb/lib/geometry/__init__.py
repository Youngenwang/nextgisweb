# -*- coding: utf-8 -*-
from __future__ import division, unicode_literals, print_function, absolute_import

from warnings import warn

from osgeo.ogr import CreateGeometryFromWkb, CreateGeometryFromWkt, wkbNDR
from pyproj import CRS, Transformer as pyTr
from shapely import wkt, wkb
from shapely.geometry import (
    mapping as geometry_mapping,
    shape as geometry_shape,
    box as geometry_box)
from shapely.ops import transform as map_coords


class GeometryNotValid(ValueError):
    pass


class Geometry(object):
    """ Initialization format is kept "as is".
    Other formats are calculated as needed."""

    __slots__ = ('_wkb', '_wkt', '_ogr', '_shape', '_srid', '_axis_xy')

    def __init__(self, wkb=None, wkt=None, ogr=None, shape=None,
                 srid=None, axis_xy=False, validate=False):
        if wkb is None and wkt is None and ogr is None and shape is None:
            raise ValueError("None base format is not defined.")

        self._wkb = wkb
        self._wkt = wkt
        self._ogr = ogr
        self._shape = shape

        self._srid = srid
        self._axis_xy = axis_xy

        if validate and (wkb is not None or wkt is not None):
            # Force WKB/WKT validation through conversion to OGR
            ogr = self.ogr

    @property
    def srid(self):
        return self._srid

    @property
    def axis_xy(self):
        return self._axis_xy

    @axis_xy.setter
    def axis_xy(self, axis_xy):
        self._axis_xy = axis_xy

    # Base constructors

    @classmethod
    def from_wkb(cls, data, srid=None, axis_xy=False, validate=True):
        return cls(wkb=data, srid=srid, axis_xy=axis_xy, validate=validate)

    @classmethod
    def from_wkt(cls, data, srid=None, axis_xy=False, validate=True):
        return cls(wkt=data, srid=srid, axis_xy=axis_xy, validate=validate)

    @classmethod
    def from_ogr(cls, data, srid=None, axis_xy=False, validate=True):
        return cls(ogr=data, srid=srid, axis_xy=axis_xy, validate=validate)

    @classmethod
    def from_shape(cls, data, srid=None, axis_xy=False, validate=False):
        return cls(shape=data, srid=srid, axis_xy=axis_xy, validate=validate)

    # Additional constructors

    @classmethod
    def from_geojson(cls, data, srid=None, validate=True):
        shape = geometry_shape(data)
        return cls.from_shape(shape, srid=srid, axis_xy=True, validate=validate)

    @classmethod
    def from_box(cls, minx, miny, maxx, maxy, axis_xy=False, srid=None):
        return cls.from_shape(
            geometry_box(minx, miny, maxx, maxy),
            srid=srid, axis_xy=axis_xy)

    # Base output formats

    @property
    def wkb(self):
        if self._wkb is None:
            if self._ogr is None and self._shape is not None:
                self._wkb = self._shape.wkb
            else:
                # ORG is the fastest, so convert to OGR and then to WKB.
                self._wkb = self.ogr.ExportToWkb(wkbNDR)
        return self._wkb

    @property
    def wkt(self):
        if self._wkt is None:
            if self._ogr is None and self._shape is not None:
                self._wkt = self._shape.wkt
            else:
                # ORG is the fastest, so convert to OGR and then to WKT.
                self._wkt = self.ogr.ExportToIsoWkt()
        return self._wkt

    @property
    def ogr(self):
        if self._ogr is None:
            if self._wkb is None and self._wkt is not None:
                self._ogr = CreateGeometryFromWkt(self._wkt)
            else:
                # WKB is the fastest, so convert to WKB and then to OGR.
                self._ogr = CreateGeometryFromWkb(self.wkb)

        if self._ogr is None:
            raise GeometryNotValid("Invalid geometry WKB/WKT value!")

        return self._ogr

    @property
    def shape(self):
        if self._shape is None:
            if self._wkb is None and self._wkt is not None:
                self._shape = wkt.loads(self._wkt)
            else:
                # WKB is the fastest, so convert to WKB and then to shape.
                self._shape = wkb.loads(self.wkb)
        return self._shape

    # Additional output formats

    def to_geojson(self):
        # NB: srid and axis order is not considered
        return geometry_mapping(self.shape)

    # Shapely providers

    @property
    def bounds(self):
        return self.shape.bounds

    def simplify(self, *args, **kwargs):
        warn("Geometry.simplify is deprecated! Use Geometry.shape object instead.",
             DeprecationWarning)
        return self.shape.simplify(*args, **kwargs)


class Transformer(object):

    def __init__(self, wkt_from, wkt_to, axis_xy):
        self.crs_from = CRS.from_wkt(wkt_from)
        self.crs_to = CRS.from_wkt(wkt_to)

        self._axis_xy = axis_xy

        # pyproj >= 2.5
        # if crs_from.equals(crs_to):
        if wkt_from == wkt_to:
            self._transformer = None
        else:
            self._transformer = pyTr.from_crs(self.crs_from, self.crs_to, always_xy=self._axis_xy)

    def transform(self, geom):
        # NB: geom.srid is not considered
        actions = []
        flip = self._axis_xy ^ geom.axis_xy
        if flip:
            if self.crs_from.is_geographic:
                actions.append(lambda x, y: (y, x))
            else:
                geom.axis_xy(self._axis_xy)
        if self._transformer is not None:
            actions.append(self._transformer.transform)

        if len(actions) == 0:
            return geom
        else:
            def operations(x, y):
                for action in actions:
                    x, y = action(x, y)
                return x, y
            shape = map_coords(operations, geom.shape)
            return Geometry.from_shape(shape)


def geom_calc(geom, crs, prop, srid):
    # pyproj < 2.3
    def geodesic_calc_with_postgis():
        # TODO: Remove these cludges after pyproj upgarade
        from sqlalchemy import func
        from ...models import DBSession

        fun = dict(length=func.ST_Length, area=func.ST_Area)[prop]
        query = fun(func.geography(func.ST_GeomFromText(geom.wkt, srid)))

        return DBSession.query(query).scalar()

    factor = crs.axis_info[0].unit_conversion_factor if len(crs.axis_info) > 0 else 1.0
    calcs = dict(
        length=lambda: geodesic_calc_with_postgis() if crs.is_geographic else geom.length * factor,
        area=lambda: geodesic_calc_with_postgis() if crs.is_geographic else geom.area * factor**2
    )

    # pyproj >= 2.3
    # calcs = dict(
    #     length=lambda: crs.get_geod().geometry_length(geom)
    #         if crs.is_geographic else geom.length * factor,
    #     area=lambda: crs.get_geod().geometry_area_perimeter(geom)[0]
    #         if crs.is_geographic else geom.area * factor**2
    # )

    if prop not in calcs:
        return None

    return calcs[prop]()
