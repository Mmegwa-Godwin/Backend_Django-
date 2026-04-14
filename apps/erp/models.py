from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

# === ACCOUNTING FIRST ===
class Account(models.Model):
    ACCOUNT_TYPES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def balance(self):
        debits = self.journal_entries.aggregate(Sum('debit'))['debit__sum'] or Decimal('0')
        credits = self.journal_entries.aggregate(Sum('credit'))['credit__sum'] or Decimal('0')
        if self.account_type in ['asset', 'expense']:
            return debits - credits
        else:
            return credits - debits

class JournalEntry(models.Model):
    date = models.DateField(default=timezone.now)
    memo = models.CharField(max_length=255)
    ref_type = models.CharField(max_length=50, blank=True)
    ref_id = models.PositiveIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"JE-{self.id} {self.date} - {self.memo}"

class JournalLine(models.Model):
    entry = models.ForeignKey(JournalEntry, related_name='lines', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, related_name='journal_entries', on_delete=models.CASCADE)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.CharField(max_length=200, blank=True)
    
    def clean(self):
        if self.debit > 0 and self.credit > 0:
            raise ValidationError("Line cannot have both debit and credit")
        if self.debit == 0 and self.credit == 0:
            raise ValidationError("Line must have debit or credit")

# === INVENTORY ===
class RawMaterial(models.Model):
    UNIT_CHOICES = [
        ('sheet', 'Sheet'), ('liter', 'Liter'), ('kg', 'KG'), 
        ('meter', 'Meter'), ('piece', 'Piece'), ('cubic_m', 'Cubic Meter')
    ]
    
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50)
    sku = models.CharField(max_length=50, unique=True)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=10)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.name} - {self.current_stock} {self.unit}"

    @property
    def needs_reorder(self):
        return self.current_stock <= self.reorder_level

class FinishedProduct(models.Model):
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50)
    sku = models.CharField(max_length=50, unique=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.name} - {self.sku}"

class BOM(models.Model):
    product = models.ForeignKey(FinishedProduct, related_name='bom_items', on_delete=models.CASCADE)
    material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    quantity_needed = models.DecimalField(max_digits=10, decimal_places=3)
    
    class Meta:
        unique_together = ['product', 'material']

# === SALES ===
class Customer(models.Model):
    name = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
    def __str__(self):
        return self.company if self.company else self.name

class SalesOrder(models.Model):
    STATUS_CHOICES = [
        ('quote', 'Quote'),
        ('confirmed', 'Confirmed'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order_number = models.CharField(max_length=20, unique=True)
    order_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='quote')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    income_account = models.ForeignKey(Account, on_delete=models.PROTECT, 
                                     limit_choices_to={'account_type': 'income'},
                                     related_name='sales_income')
    ar_account = models.ForeignKey(Account, on_delete=models.PROTECT,
                                 limit_choices_to={'account_type': 'asset'},
                                 related_name='sales_ar')
    cogs_account = models.ForeignKey(Account, on_delete=models.PROTECT,
                                   limit_choices_to={'account_type': 'expense'},
                                   related_name='sales_cogs')
    inventory_account = models.ForeignKey(Account, on_delete=models.PROTECT,
                                        limit_choices_to={'account_type': 'asset'},
                                        related_name='sales_inventory')
    
    @property
    def total(self):
        return sum(item.amount for item in self.items.all())

class SalesOrderItem(models.Model):
    order = models.ForeignKey(SalesOrder, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(FinishedProduct, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def amount(self):
        return self.quantity * self.unit_price

# === PURCHASING ===
class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    def __str__(self):
        return self.name

class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    po_number = models.CharField(max_length=20, unique=True)
    order_date = models.DateField(default=timezone.now)
    received = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    ap_account = models.ForeignKey(Account, on_delete=models.PROTECT,
                                 limit_choices_to={'account_type': 'liability'},
                                 related_name='po_ap')
    inventory_account = models.ForeignKey(Account, on_delete=models.PROTECT,
                                        limit_choices_to={'account_type': 'asset'},
                                        related_name='po_inventory')

class PurchaseOrderItem(models.Model):
    po = models.ForeignKey(PurchaseOrder, related_name='items', on_delete=models.CASCADE)
    material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

# === PRODUCTION ===
class ProductionOrder(models.Model):
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    product = models.ForeignKey(FinishedProduct, on_delete=models.CASCADE)
    quantity_to_make = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    wip_account = models.ForeignKey(Account, on_delete=models.PROTECT,
                                  limit_choices_to={'account_type': 'asset'},
                                  related_name='production_wip')
    raw_materials_inventory_account = models.ForeignKey(Account, on_delete=models.PROTECT,
                                                       limit_choices_to={'account_type': 'asset'},
                                                       related_name='production_rm')
    finished_goods_inventory_account = models.ForeignKey(Account, on_delete=models.PROTECT,
                                                        limit_choices_to={'account_type': 'asset'},
                                                        related_name='production_fg')
    
    def __str__(self):
        return f"PO-{self.id}: {self.quantity_to_make}x {self.product.name}"

    @property
    def estimated_cost(self):
        total = Decimal('0')
        for bom in self.product.bom_items.all():
            total += bom.quantity_needed * bom.material.unit_cost * self.quantity_to_make
        return total

# === PAYROLL ===
class Employee(models.Model):
    EMPLOYMENT_TYPE = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
    ]
    
    POSITION_CHOICES = [
        ('hod', 'Head of Department'),
        ('accountant', 'Accountant'),
        ('craftsman', 'Craftsman'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('intern', 'Intern'),
    ]

    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    employee_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE, default='full_time')
    job_position = models.CharField(max_length=50, choices=POSITION_CHOICES, default='staff')
    department = models.CharField(max_length=100, blank=True)
    
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=20, blank=True)
    pension_pin = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateField(default=timezone.now)

    class Meta:
        ordering = ['employee_id']

    def __str__(self):
        return f"{self.employee_id} - {self.full_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class PayrollPeriod(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
    ]

    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    salaries_expense_account = models.ForeignKey(Account, on_delete=models.PROTECT,
                                                limit_choices_to={'account_type': 'expense'},
                                                related_name='payroll_salaries')
    paye_liability_account = models.ForeignKey(Account, on_delete=models.PROTECT,
                                              limit_choices_to={'account_type': 'liability'},
                                              related_name='payroll_paye')
    pension_liability_account = models.ForeignKey(Account, on_delete=models.PROTECT,
                                                 limit_choices_to={'account_type': 'liability'},
                                                 related_name='payroll_pension')
    net_pay_liability_account = models.ForeignKey(Account, on_delete=models.PROTECT,
                                                 limit_choices_to={'account_type': 'liability'},
                                                 related_name='payroll_netpay')

    class Meta:
        unique_together = ['start_date', 'end_date']

    def __str__(self):
        return f"{self.name} - {self.status}"

    @property
    def total_gross(self):
        return self.payslips.aggregate(Sum('gross_pay'))['gross_pay__sum'] or Decimal('0')

    @property
    def total_paye(self):
        return self.payslips.aggregate(Sum('paye'))['paye__sum'] or Decimal('0')

    @property
    def total_pension_employee(self):
        return self.payslips.aggregate(Sum('pension_employee'))['pension_employee__sum'] or Decimal('0')

    @property
    def total_pension_employer(self):
        return self.payslips.aggregate(Sum('pension_employer'))['pension_employer__sum'] or Decimal('0')

    @property
    def total_net(self):
        return sum(p.net_pay for p in self.payslips.all())

class Payslip(models.Model):
    payroll_period = models.ForeignKey(PayrollPeriod, related_name='payslips', on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    gross_pay = models.DecimalField(max_digits=10, decimal_places=2)

    paye = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pension_employee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pension_employer = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ['payroll_period', 'employee']

    @property
    def total_deductions(self):
        return self.paye + self.pension_employee + self.other_deductions

    @property
    def net_pay(self):
        return self.gross_pay - self.total_deductions

    def __str__(self):
        return f"{self.employee.full_name} - {self.payroll_period.name}"

# === SIGNALS ===
@receiver(pre_save, sender=PayrollPeriod)
def post_payroll_journal(sender, instance, **kwargs):
    if not instance.pk:
        return
    
    try:
        old_instance = PayrollPeriod.objects.get(pk=instance.pk)
    except PayrollPeriod.DoesNotExist:
        return
    
    if old_instance.status != 'paid' and instance.status == 'paid':
        if JournalEntry.objects.filter(ref_type='payroll', ref_id=instance.pk).exists():
            return
            
        total_gross = instance.total_gross
        total_paye = instance.total_paye
        total_pension_emp = instance.total_pension_employee
        total_pension_employer = instance.total_pension_employer
        total_net = instance.total_net
        
        if total_gross == 0:
            return
            
        je = JournalEntry.objects.create(
            date=instance.end_date,
            memo=f"Payroll for {instance.name}",
            ref_type='payroll',
            ref_id=instance.pk,
            created_by=instance.created_by
        )
        
        JournalLine.objects.create(
            entry=je,
            account=instance.salaries_expense_account,
            debit=total_gross + total_pension_employer,
            description=f"Gross + employer pension - {instance.name}"
        )
        
        if total_paye > 0:
            JournalLine.objects.create(
                entry=je,
                account=instance.paye_liability_account,
                credit=total_paye,
                description=f"PAYE - {instance.name}"
            )
        
        total_pension = total_pension_emp + total_pension_employer
        if total_pension > 0:
            JournalLine.objects.create(
                entry=je,
                account=instance.pension_liability_account,
                credit=total_pension,
                description=f"Pension - {instance.name}"
            )
        
        if total_net > 0:
            JournalLine.objects.create(
                entry=je,
                account=instance.net_pay_liability_account,
                credit=total_net,
                description=f"Net pay - {instance.name}"
            )