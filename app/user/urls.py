"""
URLs mapping for the user APIs.
"""
from django.urls import path

from user import views


app_name = 'user'

urlpatterns = [
    path(
        'token/',
        views.CreateTokenView.as_view(),
        name='token'
    ),
    path(
        'refresh/',
        views.RefreshView.as_view(),
        name='refresh'
    ),
    path(
        'logout/',
        views.LogoutView.as_view(),
        name='logout'
    ),
    path(
        'me/',
        views.ManageUserView.as_view(),
        name='me'
    ),
    path(
        "create/",
        views.CreateUserView.as_view(),
        name="create-user"
    ),

]
