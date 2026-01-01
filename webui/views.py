from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import logout
from django.contrib.auth.models import User
from game.models import Match
import random

def home(request):
    return render(request, "home.html")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("lobby")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("lobby")
    else:
        form = UserCreationForm()

    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("lobby")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("lobby")
    else:
        form = AuthenticationForm()

    return render(request, "login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def lobby(request):
    return render(request, "lobby.html")


@login_required
def match_page(request, match_id):
    # La lógica del juego está en WS y API. Aquí solo renderizamos la pantalla.
    return render(request, "match.html", {"match_id": str(match_id)})

@login_required
def quick_match(request):
    users = list(User.objects.exclude(id=request.user.id))
    if not users:
        return redirect("lobby")

    opponent = random.choice(users)
    match = Match.objects.create(
        player1=request.user,
        player2=opponent,
        status="active",
        turn_player=1,
        board_state=[]
    )
    return redirect("match_page", match_id=match.id)