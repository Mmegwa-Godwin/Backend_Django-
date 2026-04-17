from django.shortcuts import render
from django.http import JsonResponse
from .models import Project

def home(request):
    if request.user.is_authenticated:
        projects = Project.objects.filter(owner=request.user).order_by('-created_at')
    else:
        projects = Project.objects.all().order_by('-created_at')
    
    return render(request, 'projects/home.html', {'projects': projects})

def project_list(request):
    projects = Project.objects.all().values(
        'id', 
        'title', 
        'description', 
        'github_url', 
        'live_url', 
        'image_url',
        'owner__username',
        'created_at'
    )
    return JsonResponse(list(projects), safe=False)
