from django.contrib import admin, messages
from decimal import Decimal
from.models import *

class BOMInline(admin.TabularInline):
    model = BOM
    extra = 1

class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 1

class SalesOrderItemInline(admin.TabularInline):
    model = SalesOrderItem
    extra = 1

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

class PayslipInline(admin.TabularInline):
    model = Payslip
    extra = 0
    readonly_fields = ['net_pay', 'total_deductions']

@admin.register(FinishedProduct)
class FinishedProductAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'category', 'selling_price', 'current_stock']
    inlines = [BOMInline]

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['id', 'date', 'memo', 'is_balanced', 'get_total']
    inlines = [JournalLineInline]
    readonly_fields = ['get_total', 'is_balanced']

    def get_total(self, obj):
        total = obj.lines.aggregate(Sum('debit'))['debit__sum'] or Decimal('0')
        return total
    get_total.short_description = 'Total Amount'

    def is_balanced(self, obj):
        debit = obj.lines.aggregate(Sum('debit'))['debit__sum'] or Decimal('0')
        credit = obj.lines.aggregate(Sum('credit'))['credit__sum'] or Decimal('0')
        return debit == credit
    is_balanced.boolean = True
    is_balanced.short_description = 'Balanced'

@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer', 'order_date', 'status', 'total']
    inlines = [SalesOrderItemInline]

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'supplier', 'order_date', 'received']
    inlines = [PurchaseOrderItemInline]

@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'quantity_to_make', 'status', 'estimated_cost']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'get_full_name', 'department', 'employment_type', 'is_active']
    list_filter = ['department', 'employment_type', 'is_active']
    search_fields = ['first_name', 'last_name', 'employee_id']

    def get_full_name(self, obj):
        return obj.full_name
    get_full_name.short_description = 'Name'

@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'status', 'total_gross', 'total_net']
    list_filter = ['status']
    inlines = [PayslipInline]
    readonly_fields = ['total_gross', 'total_net']
    actions = ['generate_payslips']

    def generate_payslips(self, request, queryset):
        for period in queryset:
            if period.status!= 'draft':
                self.message_user(request, f"{period.name} is not draft. Skipping.", messages.WARNING)
                continue

            employees = Employee.objects.filter(is_active=True)
            created = 0
            for emp in employees:
                obj, was_created = Payslip.objects.get_or_create(
                    payroll_period=period,
                    employee=emp,
                    defaults={
                        'gross_pay': emp.gross_salary,
                        'paye': Decimal('0'),
                        'pension_employee': emp.gross_salary * Decimal('0.08'),
                        'pension_employer': emp.gross_salary * Decimal('0.10'),
                    }
                )
                if was_created:
                    created += 1
            self.message_user(request, f"Created {created} payslips for {period.name}", messages.SUCCESS)

    generate_payslips.short_description = "Generate payslips for active employees"

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ['employee', 'payroll_period', 'gross_pay', 'paye', 'pension_employee', 'net_pay']
    list_filter = ['payroll_period']

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'account_type', 'balance']
    list_filter = ['account_type']

# Simple registrations for models without custom admin
admin.site.register(RawMaterial)
admin.site.register(Customer)
admin.site.register(Supplier)