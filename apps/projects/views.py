from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Project
from .forms import ProjectForm
from .serializers import ProjectSerializer

def home(request):
    if request.user.is_authenticated:
        # Show only your projects when logged in
        projects = Project.objects.filter(user=request.user).order_by("-created_at")
    else:
        # Show all projects to visitors, or use .none() to hide
        projects = Project.objects.all().order_by("-created_at")
    return render(request, "projects/home.html", {"projects": projects})

@api_view(["GET"])
def project_list(request):
    projects = Project.objects.all().order_by("-created_at")
    serializer = ProjectSerializer(projects, many=True)
    return Response(serializer.data)

@login_required
def add_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user  # This line needs user field in model
            project.save()
            return redirect('home')
    else:
        form = ProjectForm()
    return render(request, 'projects/add_project.html', {'form': form})