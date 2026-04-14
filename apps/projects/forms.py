from django import forms
from .models import Project

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'description', 'tech_stack', 'github_link', 'live_link']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Django Portfolio Site'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Briefly describe what it does...'}),
            'tech_stack': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Django, SQLite, Bootstrap'}),
            'github_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://github.com/username/repo'}),
            'live_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://yourdemo.com'}),
        }