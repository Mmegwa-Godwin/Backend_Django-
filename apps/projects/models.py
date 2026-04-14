from django.contrib.auth.models import User
from django.db import models


class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    title = models.CharField(max_length=200)
    description = models.TextField()
    tech_stack = models.CharField(max_length=200)
    github_link = models.URLField()
    live_link = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)