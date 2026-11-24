from django.contrib.auth.backends import ModelBackend

from .models import Users


class EmailOrUsernameBackend(ModelBackend):


    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get("username")
        if not username or password is None:
            return None
        key = username.strip()
        user = (
            Users.objects.filter(username__iexact=key).first()
            or Users.objects.filter(person__email_address__iexact=key).first()
            or Users.objects.filter(person__phone_number=key).first()
        )
        if user and user.check_password(password) and user.is_active:
            return user
        return None

    def get_user(self, user_id):
        try:
            return Users.objects.get(pk=user_id)
        except Users.DoesNotExist:
            return None
