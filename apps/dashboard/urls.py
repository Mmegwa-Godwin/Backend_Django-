from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='dashboard_home'),
    path('create/', views.create_project, name='create_project'),
    path('delete/<int:pk>/', views.delete_project, name='delete_project'),
    path('edit/<int:pk>/', views.edit_project, name='edit_project'),
]