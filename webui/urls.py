from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("lobby/", views.lobby, name="lobby"),
    path("match/<uuid:match_id>/", views.match_page, name="match_page"),
    path("quick-match/", views.quick_match, name="quick_match"),
]
