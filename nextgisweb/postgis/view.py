from ..resource import Widget
from .model import PostgisConnection, PostgisLayer


class PostgisConnectionWidget(Widget):
    resource = PostgisConnection
    operation = ('create', 'update')
    amdmod = 'ngw-postgis/ConnectionWidget'


class PostgisLayerWidget(Widget):
    resource = PostgisLayer
    operation = ('create', 'update')
    amdmod = 'ngw-postgis/LayerWidget'
