import json
from datetime import datetime
from urllib.parse import urlencode

import string
import secrets
import zope.event
import sqlalchemy as sa

from pyramid.events import BeforeRender
from pyramid.security import remember, forget
from pyramid.renderers import render_to_response
from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPUnauthorized
from sqlalchemy.orm.exc import NoResultFound

from ..models import DBSession
from ..object_widget import ObjectWidget
from ..pyramid import SessionStore, WebSession
from ..views import ModelController, permalinker
from .. import dynmenu as dm

from .models import Principal, User, Group

from .exception import InvalidCredentialsException, UserDisabledException
from .oauth import InvalidTokenException, AuthorizationException
from .util import _


class OnUserLogin(object):

    def __init__(self, user, request, next_url):
        self._user = user
        self._request = request
        self._next_url = next_url

    @property
    def user(self):
        return self._user

    @property
    def request(self):
        return self._request

    @property
    def next_url(self):
        return self._next_url

    def set_next_url(self, url):
        self._next_url = url


def login(request):
    next_url = request.params.get('next', request.application_url)

    if request.method == 'POST':
        if 'sid' in request.POST:
            sid = request.POST['sid']
            expires = request.POST['expires']

            try:
                store = SessionStore.filter_by(session_id=sid, key='auth.policy.current').one()
            except NoResultFound:
                raise InvalidCredentialsException(_("Session not found."))
            value = json.loads(store.value)

            exp = datetime.fromtimestamp(value[2])
            if datetime.fromisoformat(expires) != exp:
                raise InvalidCredentialsException(_("Invalid 'expires' parameter."))
            if exp <= datetime.utcnow():
                raise InvalidCredentialsException(_("Session expired."))

            cookie_settings = WebSession.cookie_settings(request)
            cookie_settings['expires'] = expires

            cookie_name = request.env.pyramid.options['session.cookie.name']

            response = HTTPFound(location=next_url)
            response.set_cookie(cookie_name, value=sid, **cookie_settings)

            return response
        else:
            try:
                user, headers = request.env.auth.authenticate(
                    request, request.POST['login'].strip(), request.POST['password'])
            except (InvalidCredentialsException, UserDisabledException) as exc:
                return dict(error=exc.title, next_url=next_url)

            event = OnUserLogin(user, request, next_url)
            zope.event.notify(event)

            return HTTPFound(location=event.next_url, headers=headers)

    return dict(next_url=next_url)


def session_invite(request):
    if any(k not in request.GET for k in ('sid', 'expires')):
        raise HTTPNotFound()

    return dict(
        session_id=request.GET['sid'],
        expires=request.GET['expires'],
        next_url=request.GET.get('next'))


def oauth(request):
    oaserver = request.env.auth.oauth

    oauth_url = request.route_url('auth.oauth')
    oauth_path = request.route_path('auth.oauth')

    def cookie_name(state):
        return 'ngw-oastate-' + state

    if 'error' in request.params:
        raise AuthorizationException()

    elif 'code' in request.params and 'state' in request.params:
        # Extract data from state named cookie
        state = request.params['state']
        try:
            data = json.loads(request.cookies[cookie_name(state)])
        except ValueError:
            raise AuthorizationException("State cookie parse error")

        tresp = oaserver.grant_type_authorization_code(
            request.params['code'], oauth_url)

        if data['merge'] == '1' and request.user.keyname != 'guest':
            user = oaserver.access_token_to_user(tresp.access_token, merge_user=request.user)
        else:
            user = oaserver.access_token_to_user(tresp.access_token)

        if user is None:
            raise InvalidTokenException()

        DBSession.flush()
        headers = remember(request, (user.id, tresp))

        event = OnUserLogin(user, request, data['next_url'])
        zope.event.notify(event)

        response = HTTPFound(location=event.next_url, headers=headers)
        response.delete_cookie(cookie_name(state), path=oauth_path)
        return response

    else:
        data = dict(
            next_url=request.params.get('next', request.application_url),
            merge=request.params.get('merge', '0')
        )

        alphabet = string.ascii_letters + string.digits
        state = ''.join(secrets.choice(alphabet) for i in range(16))
        ac_url = oaserver.authorization_code_url(oauth_url, state=state)

        response = HTTPFound(location=ac_url)

        # Store data in state named cookie
        response.set_cookie(
            cookie_name(state), value=json.dumps(data),
            path=oauth_path, max_age=600, httponly=True)

        return response


def logout(request):
    oaserver = request.env.auth.oauth

    location = request.application_url

    if oaserver is not None:
        logout_endpoint = oaserver.options.get('server.logout_endpoint')
        if logout_endpoint is not None:
            current = request.session.get('auth.policy.current')
            if current is not None and current[0] == 'OAUTH':
                qs = dict(redirect_uri=request.application_url)
                location = logout_endpoint + '?' + urlencode(qs)

    headers = forget(request)

    return HTTPFound(location=location, headers=headers)


def _login_url(request):
    """ Request method for getting preferred login url (local or OAuth) """

    auth = request.env.auth

    login_qs = dict()
    if request.matched_route is None or request.matched_route.name not in (
        auth.options['login_route_name'], auth.options['logout_route_name']
    ):
        login_qs['next'] = request.url

    oauth_opts = auth.options.with_prefix('oauth')
    if oauth_opts['enabled'] and oauth_opts['default'] and not oauth_opts['server.password']:
        login_url = request.route_url('auth.oauth', _query=login_qs)
    else:
        login_url = request.route_url(auth.options['login_route_name'], _query=login_qs)

    return login_url


def forbidden_error_handler(request, err_info, exc, exc_info, **kwargs):
    # If user is not authentificated, we can offer him to sign in
    if (
        request.method == 'GET'
        and not request.is_api and not request.is_xhr
        and err_info.http_status_code == 403
        and request.authenticated_userid is None
    ):
        response = render_to_response('nextgisweb:auth/template/login.mako', dict(
            auth_required=(
                request.env.auth.options['oauth.enabled']
                and request.env.auth.options['oauth.default']
            ), next_url=request.url,
        ), request=request)
        response.status = 403
        return response


def settings(request):
    if request.user.keyname == 'guest':
        return HTTPUnauthorized()

    return dict(title=_("User settings"))


def setup_pyramid(comp, config):
    # Add it before default pyramid handlers
    comp.env.pyramid.error_handlers.insert(0, forbidden_error_handler)

    def check_permission(request):
        """ To avoid interdependency of two components:
        auth and security, permissions to edit users
        are limited by administrators group membership criterion"""

        request.require_administrator()

    config.add_route('auth.login', '/login') \
        .add_view(login, renderer='nextgisweb:auth/template/login.mako')

    config.add_route(
        'pyramid.session.invite',
        '/session/invite'
    ).add_view(session_invite, renderer='nextgisweb:auth/template/session_invite.mako')

    config.add_route('auth.logout', '/logout').add_view(logout)

    config.add_route('auth.oauth', '/oauth').add_view(oauth)

    config.add_route('auth.settings', '/settings') \
        .add_view(settings, renderer='nextgisweb:auth/template/settings.mako')

    config.add_request_method(_login_url, name='login_url')

    def principal_dump(request):
        query = Principal.query().with_polymorphic('*')
        result = []

        for p in query:
            result.append(dict(
                id=p.id,
                cls=p.cls,
                system=p.system,
                keyname=p.keyname,
                display_name=p.display_name
            ))

        return result

    config.add_route('auth.principal_dump', '/auth/principal/dump') \
        .add_view(principal_dump, renderer='json')

    class AuthGroupWidget(ObjectWidget):

        def is_applicable(self):
            return self.operation in ('create', 'edit')

        def populate_obj(self):
            super().populate_obj()

            self.obj.deserialize(self.data)

        def validate(self):
            result = super().validate()
            self.error = []

            if self.operation in ('create', 'edit'):
                query = Group.filter_by(
                    keyname=self.data.get("keyname"))
                if self.operation == 'edit':
                    query = query.filter(Group.id != self.obj.id)
                conflict = query.first()
                if conflict:
                    result = False
                    self.error.append(dict(
                        message=self.request.localizer.translate(
                            _("Group name is not unique."))))

            return result

        def widget_params(self):
            result = super().widget_params()

            if self.obj:
                result['value'] = dict(
                    display_name=self.obj.display_name,
                    keyname=self.obj.keyname,
                    description=self.obj.description,
                    register=self.obj.register)

                result['users'] = [
                    dict(
                        value=u.id,
                        label=u.display_name,
                        selected=u in self.obj.members
                    ) for u in User.filter_by(system=False)]

            else:
                # List of all users for selector
                result['users'] = [
                    dict(value=u.id, label=u.display_name)
                    for u in User.filter_by(system=False)
                ]

            return result

        def widget_module(self):
            return 'ngw-auth/GroupWidget'

    class GroupController(ModelController):

        def create_context(self, request):
            check_permission(request)
            return dict(template=dict(
                subtitle=_("Create new group"),
                dynmenu=Group.__dynmenu__))

        def edit_context(self, request):
            check_permission(request)
            obj = Group.filter_by(**request.matchdict) \
                .filter_by(system=False).one()

            return dict(
                obj=obj,
                template=dict(obj=obj)
            )

        def create_object(self, context):
            return Group()

        def query_object(self, context):
            return context['obj']

        def widget_class(self, context, operation):
            return AuthGroupWidget

        def template_context(self, context):
            return context['template']

    GroupController('auth.group', '/auth/group').includeme(config)

    class AuthUserWidget(ObjectWidget):

        def is_applicable(self):
            return self.operation in ('create', 'edit')

        def populate_obj(self):
            super().populate_obj()

            self.obj.deserialize(self.data)

        def validate(self):
            result = super().validate()
            self.error = []

            if self.operation in ('create', 'edit'):
                query = User.filter(
                    sa.func.lower(User.keyname) == self.data.get("keyname").lower())
                if self.operation == 'edit':
                    query = query.filter(User.id != self.obj.id)
                conflict = query.first()
                if conflict:
                    result = False
                    self.error.append(dict(
                        message=self.request.localizer.translate(
                            _("Login is not unique."))))

            if self.operation == 'edit':
                disabled = self.data.get('disabled', False)
                if disabled or 'member_of' in self.data:
                    admins = Group.filter_by(keyname='administrators').one()
                    if not disabled and admins.id in self.data['member_of']:
                        pass
                    elif not any([
                        user for user in admins.members
                        if not user.disabled and user.principal_id != self.obj.principal_id
                    ]):
                        result = False
                        self.error.append(dict(
                            message=self.request.localizer.translate(
                                _("You can't disable current administrator. At least one enabled administrator is required."))))  # NOQA

            return result

        def widget_params(self):
            result = super().widget_params()

            if self.obj:
                result['value'] = dict(
                    display_name=self.obj.display_name,
                    keyname=self.obj.keyname,
                    superuser=self.obj.superuser,
                    disabled=self.obj.disabled,
                    language=self.obj.language,
                    oauth_subject=self.obj.oauth_subject,
                    member_of=[m.id for m in self.obj.member_of],
                    description=self.obj.description,
                )
                result['groups'] = [
                    dict(
                        value=g.id,
                        label=g.display_name,
                        selected=g in self.obj.member_of
                    )
                    for g in Group.query()
                ]

            else:
                # List of all groups to selection field
                result['groups'] = [
                    dict(value=g.id, label=g.display_name)
                    for g in Group.query()
                ]

            return result

        def widget_module(self):
            return 'ngw-auth/UserWidget'

    class AuthUserModelController(ModelController):

        def create_context(self, request):
            check_permission(request)
            return dict(template=dict(
                subtitle=_("Create new user"),
                dynmenu=User.__dynmenu__))

        def edit_context(self, request):
            check_permission(request)
            obj = User.filter_by(**request.matchdict) \
                .filter_by(system=False).one()

            return dict(
                obj=obj,
                template=dict(obj=obj)
            )

        def create_object(self, context):
            return User()

        def query_object(self, context):
            return context['obj']

        def widget_class(self, context, operation):
            return AuthUserWidget

        def template_context(self, context):
            return context['template']

    AuthUserModelController('auth.user', '/auth/user').includeme(config)

    permalinker(Group, "auth.group.edit")
    permalinker(User, "auth.user.edit")

    def user_browse(request):
        check_permission(request)
        return dict(
            title=_("Users"),
            obj_list=User.filter_by(system=False).order_by(User.display_name),
            dynmenu=request.env.pyramid.control_panel)

    config.add_route('auth.user.browse', '/auth/user/') \
        .add_view(user_browse, renderer='nextgisweb:auth/template/user_browse.mako')

    def group_browse(request):
        check_permission(request)
        return dict(
            title=_("Groups"),
            obj_list=Group.filter_by(system=False).order_by(Group.display_name),
            dynmenu=request.env.pyramid.control_panel)

    config.add_route('auth.group.browse', '/auth/group/') \
        .add_view(group_browse, renderer='nextgisweb:auth/template/group_browse.mako')

    class UserMenu(dm.DynItem):

        def build(self, kwargs):
            yield dm.Link(
                self.sub('browse'), _("List"),
                lambda kwargs: kwargs.request.route_url('auth.user.browse')
            )

            yield dm.Link(
                self.sub('create'), _("Create"),
                lambda kwargs: kwargs.request.route_url('auth.user.create')
            )

            if 'obj' in kwargs and isinstance(kwargs.obj, User):
                yield dm.Link(
                    self.sub('edit'), _("Edit"),
                    lambda kwargs: kwargs.request.route_url(
                        'auth.user.edit',
                        id=kwargs.obj.id
                    )
                )

    class GroupMenu(dm.DynItem):

        def build(self, kwargs):
            yield dm.Link(
                self.sub('browse'), _("List"),
                lambda kwargs: kwargs.request.route_url('auth.group.browse')
            )

            yield dm.Link(
                self.sub('create'), _("Create"),
                lambda kwargs: kwargs.request.route_url('auth.group.create')
            )

            if 'obj' in kwargs and isinstance(kwargs.obj, Group):
                yield dm.Link(
                    self.sub('edit'), _("Edit"),
                    lambda kwargs: kwargs.request.route_url(
                        'auth.group.edit',
                        id=kwargs.obj.id
                    )
                )

    User.__dynmenu__ = comp.env.pyramid.control_panel
    Group.__dynmenu__ = comp.env.pyramid.control_panel

    comp.env.pyramid.control_panel.add(
        dm.Label('auth-user', _("Users")),
        UserMenu('auth-user'),

        dm.Label('auth-group', _("Groups")),
        GroupMenu('auth-group'),
    )

    # Login and logout routes names
    def add_globals(event):
        event['login_route_name'] = comp.options['login_route_name']
        event['logout_route_name'] = comp.options['logout_route_name']

    config.add_subscriber(add_globals, BeforeRender)
