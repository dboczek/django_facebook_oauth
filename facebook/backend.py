import cgi, urllib, json

from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.db import IntegrityError

profile_module = __import__('.'.join(settings.AUTH_PROFILE_MODULE.split('.')[:-1]))
FacebookProfile = getattr(profile_module.models,settings.AUTH_PROFILE_MODULE.split('.')[-1])

class FacebookBackend:
    def update_facebook_info(self, fb_user, fb_profile, access_token):
        def updateAccessToken():
            fb_user.access_token = access_token
        def updateGender():
            if fb_profile['gender'] == 'male':
                fb_user.gender = 'm'
            elif fb_profile['gender'] == 'female':
                fb_user.gender = 'f'
        def updateNameAndSurname():
            fb_user.name = fb_profile['first_name']
            fb_user.surname = fb_profile['last_name']
            
        updateAccessToken()
        updateGender()
        updateNameAndSurname()
        fb_user.save()
        
    def authenticate(self, token=None, request=None):
        """ Reads in a Facebook code and asks Facebook if it's valid and what user it points to. """
        args = {
            'client_id': settings.FACEBOOK_APP_ID,
            'client_secret': settings.FACEBOOK_APP_SECRET,
            'redirect_uri': request.build_absolute_uri('/facebook/authentication_callback'),
            'code': token,
        }

        # Get a legit access token
        target = urllib.urlopen('https://graph.facebook.com/oauth/access_token?' + urllib.urlencode(args)).read()
        response = cgi.parse_qs(target)
        access_token = response['access_token'][-1]

        # Read the user's profile information
        fb_profile = urllib.urlopen('https://graph.facebook.com/me?access_token=%s' % access_token)
        fb_profile = json.load(fb_profile)
        
        try:
            # Try and find existing user
            fb_user = FacebookProfile.objects.get(facebook_id=fb_profile['id'])
            user = fb_user.user

            self.update_facebook_info(fb_user, fb_profile, access_token)

        except FacebookProfile.DoesNotExist:
            # No existing user

            # Not all users have usernames
            username = fb_profile.get('username', fb_profile['email'].split('@')[0])

            if getattr(settings, 'FACEBOOK_FORCE_SIGNUP', False):
                # No existing user, use anonymous
                user = AnonymousUser()
                user.username = username
                user.first_name = fb_profile['first_name']
                user.last_name = fb_profile['last_name']
                fb_user = FacebookProfile(
                        facebook_id=fb_profile['id']
                )
                self.update_facebook_info(fb_user, fb_profile, access_token)
                user.facebookprofile = fb_user

            else:
                # No existing user, create one

                try:
                    user = User.objects.create_user(username, fb_profile['email'])
                except IntegrityError:
                    # Username already exists, make it unique
                    user = User.objects.create_user(username + fb_profile['id'], fb_profile['email'])
                user.first_name = fb_profile['first_name']
                user.last_name = fb_profile['last_name']
                user.save()

                # Create the FacebookProfile
                fb_user = FacebookProfile(user=user, facebook_id=fb_profile['id'])
                
                self.update_facebook_info(fb_user, fb_profile, access_token)

        return user

    def get_user(self, user_id):
        """ Just returns the user of a given ID. """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    supports_object_permissions = False
    supports_anonymous_user = True
