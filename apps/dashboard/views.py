from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.projects.models import Project
@login_required
def home(request):
    projects = Project.objects.all()

    total_projects = projects.count()

    return render(request, "dashboard/home.html", {
        "projects": projects,
        "total_projects": total_projects
    })
@login_required
def create_project(request):
    if request.method == "POST":
        Project.objects.create(
            title=request.POST['title'],
            description=request.POST['description'],
            tech_stack=request.POST['tech_stack'],
            github_link=request.POST['github_link'],
            live_link=request.POST.get('live_link', '')
        )
        return redirect('dashboard_home')

    return render(request, "dashboard/create.html")
@login_required
def delete_project(request, pk):
    project = get_object_or_404(Project, id=pk)
    project.delete()
    return redirect('dashboard_home')
@login_required
def edit_project(request, pk):
    project = get_object_or_404(Project, id=pk)

    if request.method == "POST":
        project.title = request.POST['title']
        project.description = request.POST['description']
        project.tech_stack = request.POST['tech_stack']
        project.github_link = request.POST['github_link']
        project.live_link = request.POST.get('live_link', '')
        project.save()

        return redirect('dashboard_home')

    return render(request, "dashboard/edit.html", {"project": project})

