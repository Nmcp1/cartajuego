from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    mmr = models.IntegerField(default=1000)
    coins = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} ({self.mmr})"
