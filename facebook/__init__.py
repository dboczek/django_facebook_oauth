import fbgraph

class FacebookException(Exception): pass

class Facebook(object):
    """
    Simple Facebook proxy
    """

    def __init__(self, uid=None, access_token=None, url=None):
        """
        Args:
            uid (str): Facebook user identifier
            access_token (str): facebook access token 
        """
        self.uid = uid
        self.graph = fbgraph.GraphAPI(access_token, url=url)
        self._profile = None

        if self.graph.access_token and not self.uid:
            self.uid = self.get_user_id()

    def get_profile(self):
        """
        Fetch authenticated user profile data
        """
        if not self._profile or not self._profile['id']==self.uid:
            self._profile = self.graph.get_object('me')
        return self._profile

    def get_user_id(self):
        return self.graph.get_object('me', fields='id').get('id')
            
    def fetch_access_token(self, *args, **kw):
        self.graph.fetch_access_token(*args, **kw)
        self.fetch_uid_if_none()
        return self.graph.access_token


    def fetch_uid_if_none(self):
        if not self.uid and self.graph.access_token:
            self.uid = self.get_user_id()

    def set_access_token(self, access_token):
        self.graph.access_token = access_token
        self.fetch_uid_if_none()

    def authorized(self):
        return bool(self.uid)

    @property
    def access_token(self):
        return self.graph.access_token


def create_facebook_proxy(request, redirect_uri=''):
    """
    Common Facebook proxy factory. 
    Uses FB cookie or request method (by `code` argument).

    `FACEBOOK_APP_ID` and `FACEBOOK_SECRET_KEY` comes from settings.

    Args:
        request: Django Request instance
        redirect_uri: Facebook redirect URI (required for "request" method)

    Returns:
        Preconfigured Facebook proxy instance
    """

    from django.conf import settings
    facebook_url = getattr(settings, 'FACEBOOK_URL', None)

    # request method
    if 'code' in request.GET:
        if not redirect_uri:
            raise ValueError('Redirect URI is required')
        proxy = Facebook(url=facebook_url)
        access_token = request.session.get('FACEBOOK_ACCESS_TOKEN')
        session_code = request.session.get('FACEBOOK_CODE')
        if request.GET['code'] != session_code:
            access_token = proxy.fetch_access_token(
                    code=request.GET['code'],
                    app_id=settings.FACEBOOK_APP_ID,
                    app_secret=settings.FACEBOOK_APP_SECRET,
                    redirect_uri=redirect_uri
                )
        else:
            proxy.set_access_token(access_token)
        request.session['FACEBOOK_ACCESS_TOKEN'] = access_token
        request.session['FACEBOOK_CODE'] = code=request.GET['code']
        return proxy

    # cookie method
    fb_user = fbgraph.get_user_from_cookie(request.COOKIES,
        settings.FACEBOOK_APP_ID, settings.FACEBOOK_APP_SECRET)

    if fb_user:
        return Facebook(fb_user['uid'], fb_user['access_token'],
                url=facebook_url)

    return Facebook(url=facebook_url)


