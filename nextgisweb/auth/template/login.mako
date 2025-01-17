<%inherit file="nextgisweb:pyramid/template/base.mako" />
<%! from nextgisweb.auth.util import _ %>

<form class="auth-form pure-form pure-form-stacked" 
    action="${request.route_url('auth.login')}" method="POST">

    %if not next_url is UNDEFINED:
        <input type="hidden" name="next" value="${next_url}">
    %endif

    <h1 class="auth-form__title">
        %if auth_required:
            ${tr(_('Authorization Required'))}
        %else:
            ${tr(_('Sign in to Web GIS'))}
        %endif
    </h1>

    %if error:
        <div class="auth-form__error">${error}</div>
    %endif

    %if auth_required:
        <a class="dijit dijitReset dijitInline dijitButton--primary dijitButton"
            href="${request.login_url()}">
            <span class="dijitReset dijitInline dijitButtonNode">
                ${tr(_('Sign in with OAuth'))}
            </span>
        </a>
    %else:
        %if (request.env.auth.oauth is not None) and (not request.env.auth.oauth.password):
            <% oauth_url = request.route_url('auth.oauth', _query=dict(next=next_url) if next_url else None) %>
            <div class="pure-control-group">
                <a class="dijit dijitReset dijitInline dijitButton--primary dijitButton"
                    href="${oauth_url}">
                    <span class="dijitReset dijitInline dijitButtonNode">
                        ${tr(_('Sign in with OAuth'))}
                    </span>
                </a>
            </div>
        %endif

        <div class="pure-control-group">
            <input autofocus name="login" type="text" required placeholder="${tr(_('Login'))}">
        </div>
        <div class="pure-control-group">
            <input name="password" type="password" required placeholder="${tr(_('Password'))}">
        </div>
        <button class="auth-form__btn dijit dijitReset dijitInline dijitButton--primary dijitButton"
                type="submit" value="" class="pure-button pure-button-primary">
            <span class="dijitReset dijitInline dijitButtonNode" >
                <span>
                    ${tr(_('Sign in'))}
                </span>
            </span>
        </button>
    %endif
</form>
