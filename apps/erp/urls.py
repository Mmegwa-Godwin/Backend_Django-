from django.urls import path
from . import views

app_name = 'erp'

urlpatterns = [
    path('me/', views.employee_dashboard, name='employee_dashboard'),
    path('payslip/<int:pk>/pdf/', views.payslip_pdf, name='payslip_pdf'),

]
