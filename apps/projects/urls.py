from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.home, name='home'),
    path('api/projects/', views.project_list, name='project_list'),
]
