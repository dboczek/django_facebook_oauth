from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
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
        except IOError:
            message = _('Could not connect to Facebook')
        except GraphAPIError, e:
            message = unicode(e)
        ctx = {
            'message': message,
            }
        return render_to_response(template_name, RequestContext(request, ctx))
    return wrapped


@catch_connection_error
def facebook_login(request, template_name='facebook/login.html',
        fail_template_name='facebook/failed.html',
        extra_context=None, form_class=CreateUserForm,
        success_url=settings.LOGIN_REDIRECT_URL):
    """
    Facebook callback view
    """

    fb = facebook.create_facebook_proxy(request,
            request.build_absolute_uri(reverse('facebook-login')))

    if not fb.authorized():
        ctx = extra_context or {}
        ctx.update({
            'message': _('We couldn\'t validate your Facebook credentials.'),
            })
        return render_to_response(fail_template_name, RequestContext(request, ctx))


    if request.method == 'POST':
        fbprofile = fb.get_profile()
        form = form_class(request, data=request.POST, initial=fbprofile)
        if form.is_valid():
            form.save()
            user = authenticate(facebook_uid=fb.uid)
            if user:
                signals.facebook_connect.send(sender=facebook_login,
                        instance=user, fbprofile=fbprofile, graph=fb.graph)
                login(request, user)
            return redirect(success_url)
    else:

        # try to authenticate previously connected facebook user
        # using facebook User ID
        
        user = authenticate(facebook_uid=fb.uid)

        if user:
            # user authenticated
            signals.facebook_login.send(sender=facebook_login,
                    instance=user, graph=fb.graph)
            login(request, user)
            return redirect(success_url)

        fbprofile = fb.get_profile()
        form = form_class(request, initial=fbprofile)

    ctx = {
            'form': form,
            }
    return render_to_response(template_name, RequestContext(request, ctx))


