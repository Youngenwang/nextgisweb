from collections import OrderedDict

from ..lib.config import Option
from ..component import Component, require

from .feature import Feature, FeatureSet
from .model import Base, LayerField, LayerFieldsMixin
from .interface import (
    GEOM_TYPE,
    GEOM_TYPE_OGR,
    FIELD_TYPE,
    FIELD_TYPE_OGR,
    IFeatureLayer,
    IFieldEditableFeatureLayer,
    IWritableFeatureLayer,
    IFeatureQuery,
    IFeatureQueryFilter,
    IFeatureQueryFilterBy,
    IFeatureQueryOrderBy,
    IFeatureQueryLike,
    IFeatureQueryIntersects,
    IFeatureQueryClipByBox,
    IFeatureQuerySimplify,
)
from .event import on_data_change
from .extension import FeatureExtension
from .api import query_feature_or_not_found
from .ogrdriver import OGR_DRIVER_NAME_2_EXPORT_FORMATS

__all__ = [
    'Feature',
    'FeatureSet',
    'LayerField',
    'LayerFieldsMixin',
    'GEOM_TYPE',
    'GEOM_TYPE_OGR',
    'FIELD_TYPE',
    'FIELD_TYPE_OGR',
    'IFeatureLayer',
    'IFieldEditableFeatureLayer',
    'IWritableFeatureLayer',
    'IFeatureQuery',
    'IFeatureQueryFilter',
    'IFeatureQueryFilterBy',
    'IFeatureQueryOrderBy',
    'IFeatureQueryLike',
    'IFeatureQueryIntersects',
    'IFeatureQueryClipByBox',
    'IFeatureQuerySimplify',
    'on_data_change',
    'query_feature_or_not_found',
]


class FeatureLayerComponent(Component):
    identity = 'feature_layer'
    metadata = Base.metadata

    def initialize(self):
        self.FeatureExtension = FeatureExtension

    @require('resource')
    def setup_pyramid(self, config):
        from . import view, api
        view.setup_pyramid(self, config)
        api.setup_pyramid(self, config)

    def client_settings(self, request):
        editor_widget = OrderedDict()
        for k, ecls in FeatureExtension.registry._dict.items():
            if hasattr(ecls, 'editor_widget'):
                editor_widget[k] = ecls.editor_widget

        return dict(
            editor_widget=editor_widget,
            extensions=dict(map(
                lambda ext: (ext.identity, ext.display_widget),
                FeatureExtension.registry
            )),
            export_formats=OGR_DRIVER_NAME_2_EXPORT_FORMATS,
            datatypes=FIELD_TYPE.enum,
        )
