from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.projects.models import Project
from apps.accounts.models import Profile

@login_required
def dashboard_view(request):
    user = request.user
    projects_count = Project.objects.filter(owner=user).count() if hasattr(Project, 'owner') else Project.objects.count()
    recent_projects = Project.objects.all()[:3]  # swap to filter(owner=user) later
    
    context = {
        'projects_count': projects_count,
        'recent_projects': recent_projects,
    }
    return render(request, 'dashboard/index.html', context)
