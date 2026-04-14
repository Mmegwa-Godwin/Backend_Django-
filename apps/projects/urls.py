from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/projects/', views.project_list, name='project_list'),
    path('add_project/', views.add_project, name='add_project'),
]