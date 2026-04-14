from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from .models import Employee, Payslip, PayrollPeriod

@login_required
def employee_dashboard(request):
    employee = get_object_or_404(Employee, user=request.user)
    
    # Get all payslips for this employee, newest first
    payslips = Payslip.objects.filter(employee=employee).select_related('payroll_period').order_by('-payroll_period__start_date')
    
    # YTD calculations - Jan 1st to now
    current_year = timezone.now().year
    ytd_payslips = payslips.filter(payroll_period__start_date__year=current_year)
    
    ytd_gross = ytd_payslips.aggregate(total=Sum('gross_pay'))['total'] or Decimal('0')
    ytd_paye = ytd_payslips.aggregate(total=Sum('paye'))['total'] or Decimal('0')
    ytd_pension = ytd_payslips.aggregate(total=Sum('pension_employee'))['total'] or Decimal('0')
    ytd_net = ytd_payslips.aggregate(total=Sum('net_pay'))['total'] or Decimal('0')
    
    context = {
        'employee': employee,
        'payslips': payslips[:12],  # Last 12 payslips
        'ytd_gross': ytd_gross,
        'ytd_paye': ytd_paye,
        'ytd_pension': ytd_pension,
        'ytd_net': ytd_net,
    }
    return render(request, 'erp/employee_dashboard.html', context)
    
@login_required
def payslip_pdf(request, pk):
    payslip = get_object_or_404(Payslip, pk=pk)
    if payslip.employee.user != request.user and not request.user.is_staff:
        return HttpResponse("Unauthorized", status=403)
    
    # Placeholder for now - returns plain text
    content = f"""
    PAYSLIP
    Employee: {payslip.employee.full_name}
    Employee ID: {payslip.employee.employee_id}
    Period: {payslip.payroll_period.name}
    Date: {payslip.payroll_period.end_date}
    
    EARNINGS
    Gross Pay: ₦{payslip.gross_pay:,.2f}
    
    DEDUCTIONS
    PAYE Tax: ₦{payslip.paye:,.2f}
    Pension (Employee 8%): ₦{payslip.pension_employee:,.2f}
    Other Deductions: ₦{payslip.other_deductions:,.2f}
    Total Deductions: ₦{payslip.total_deductions:,.2f}
    
    NET PAY: ₦{payslip.net_pay:,.2f}
    
    Employer Pension Contribution: ₦{payslip.pension_employer:,.2f}
    """
    return HttpResponse(content, content_type='text/plain')
