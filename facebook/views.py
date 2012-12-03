from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.urlresolvers import reverse
from django.db import transaction, IntegrityError
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.generic.edit import FormView
from forms import CreateUserForm
import facebook
from fbgraph import GraphAPIError
import urllib
import signals


def redirect_to_facebook_auth(request):
    """ First step of process, redirects user to facebook, which redirects to authentication_callback. """

    args = {
        'client_id': settings.FACEBOOK_APP_ID,
        'scope': settings.FACEBOOK_SCOPE,
        'redirect_uri': request.build_absolute_uri(reverse('facebook-login')),
    }
    return redirect('https://www.facebook.com/dialog/oauth?' + urllib.urlencode(args))


def catch_connection_error(func, template_name='facebook/failed.html'):
    """
    wrapper for Facebook connection error 
    """
    def wrapped(request, *args, **kw):
        message = _('Unknown error')
        try:
            return func(request, *args, **kw)
        except (IOError, ValueError):
            message = _('Could not connect to Facebook')
        except GraphAPIError, e:
            message = unicode(e)
        except IntegrityError, e:
            # retrying user login in case of race condition
            if "auth_user_username_key" in e.message\
            or "facebook_facebookprofile_user_id_key" in e.message:
                return redirect(reverse('facebook-auth'))
            raise
        ctx = {
            'message': message,
            }
        return render_to_response(template_name, RequestContext(request, ctx))
    return wrapped


def facebook_inactive_user(request, template_name=None):
    ctx = {}
    return render_to_response(template_name or 'facebook/inactive_user.html',
            RequestContext(request, ctx))


class FacebookLoginView(FormView):
    form_class = CreateUserForm
    success_url = settings.LOGIN_REDIRECT_URL
    inactive_account_url = None 
    confirmation_url = None 
    facebook_login_url = None
    fail_template_name = 'facebook/failed.html'
    template_name = 'facebook/login.html'

    def get_facebook_proxy(self, request):
        return facebook.create_facebook_proxy(request,
                request.build_absolute_uri(self.get_facebook_login_url()))

    @method_decorator(transaction.commit_on_success)
    @method_decorator(catch_connection_error)
    def dispatch(self, request, *args, **kw):
        self.fbproxy = self.get_facebook_proxy(request)
        self._user_logged = False
        return super(FacebookLoginView, self).dispatch(request, *args, **kw)

    def get_context_data(self, **kw):
        if not self.fbproxy.authorized():
            return {
                'message': _('We couldn\'t validate your Facebook credentials.'),
                }
        return super(FacebookLoginView, self).get_context_data(**kw)

    def get_template_names(self):
        if not self.fbproxy.authorized():
            return [self.fail_template_name]
        return super(FacebookLoginView, self).get_template_names()

    def get_initial(self):
        if self.fbproxy.authorized():
            return self.fbproxy.get_profile()
        return {}

    def get_form(self, form_class):
        return form_class(self.request, **self.get_form_kwargs())

    def get_inactive_account_url(self):
        return self.inactive_account_url or reverse('facebook-inactive-user')

    def get_facebook_login_url(self):
        return self.facebook_login_url or reverse('facebook-login')

    def get_confirmation_url(self):
        return self.confirmation_url or self.get_inactive_account_url()

    def inactive_user(self, user):
        """
        called when trying to login inactive user
        """
        return redirect(self.get_inactive_account_url())

    def confirm_user(self, user):
        """
        called when user confirmation is needed
        """
        return redirect(self.get_confirmation_url())

    def login_user(self, user):
        """
        called when logging user
        """
        signals.facebook_login.send(sender=facebook_login,
                instance=user, graph=self.fbproxy.graph)
        login(self.request, user)
        return redirect(self.get_success_url())

    def connect_user(self, user, form):
        """
        called when connecting new user
        """
        login(self.request, user)
        signals.facebook_connect.send(sender=facebook_login, instance=user, 
            fbprofile=self.fbproxy.get_profile(), graph=self.fbproxy.graph)
        return redirect(self.get_success_url())

    def get(self, *args, **kw):
        if self.fbproxy.authorized():
            user = authenticate(facebook_uid=self.fbproxy.uid)
            if user and user.is_active:
                # user authenticated
                return self.login_user(user)
            elif user:
                # user has inactive account
                return self.inactive_user(user)
        return super(FacebookLoginView, self).get(*args, **kw)

    def form_valid(self, form):
        form.save()
        user = authenticate(facebook_uid=self.fbproxy.uid)
        if user and user.is_active:
            return self.connect_user(user, form)
        return self.confirm_user(user)



facebook_login = FacebookLoginView.as_view()
