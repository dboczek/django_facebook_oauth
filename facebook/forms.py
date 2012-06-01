from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms


class CreateUserForm(UserCreationForm):
    class Meta:
        model = User

    def __init__(self, request, *args, **kw):
        super(CreateUserForm, self).__init__(*args, **kw)

