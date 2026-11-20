from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .models import Expense, Category
from .forms import RegisterForm, ExpenseForm
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from django.utils import timezone
def register(request):

    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')

    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})

def user_login(request):

    from django.contrib.auth.forms import AuthenticationForm

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')

    else:
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {'form': form})

@login_required
def user_logout(request):

    if request.method == 'POST':
        logout(request)

    return redirect('login')

@login_required
def dashboard(request):

    expenses = Expense.objects.filter(user=request.user)

    total_income = expenses.filter(
        transaction_type='income'
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_expense = expenses.filter(
        transaction_type='expense'
    ).aggregate(total=Sum('amount'))['total'] or 0

    balance = total_income - total_expense

    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'recent_transactions': expenses.order_by('-date', '-id')[:5],
    }

    return render(request, 'expenses/dashboard.html', context)

@login_required
def add_expense(request):

    if request.method == 'POST':
        form = ExpenseForm(request.POST)

        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            messages.success(request, 'Transaction added successfully!')
            return redirect('dashboard')

    else:
        form = ExpenseForm()

    return render(request, 'expenses/add_expense.html', {'form': form})

@login_required
def expense_list(request):

    expenses = Expense.objects.filter(
        user=request.user
    ).order_by('-date', '-id')

    return render(
        request,
        'expenses/expense_list.html',
        {'expenses': expenses}
    )

@login_required
def edit_expense(request, expense_id):

    expense = get_object_or_404(
        Expense,
        id=expense_id,
        user=request.user
    )

    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)

        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction updated successfully!')
            return redirect('expense_list')

    else:
        form = ExpenseForm(instance=expense)

    return render(
        request,
        'expenses/edit_expense.html',
        {'form': form}
    )

@login_required
def delete_expense(request, expense_id):

    expense = get_object_or_404(
        Expense,
        id=expense_id,
        user=request.user
    )

    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Transaction deleted successfully!')

    return redirect('expense_list')

@login_required
def download_transactions_pdf(request):
    expenses = Expense.objects.filter(
        user=request.user
    ).order_by('-date', '-id')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="transactions.pdf"'

    pdf = SimpleDocTemplate(
        response,
        pagesize=landscape(A4)
    )

    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Expense Manager - Transaction History", styles['Title']))
    elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph(
        f"User: {request.user.username}",
        styles['Normal']
    ))

    elements.append(Paragraph(
        f"Generated on: {timezone.localdate().strftime('%d %B %Y')}",
        styles['Normal']
    ))

    elements.append(Spacer(1, 0.3 * inch))

    data = [
        ['Date', 'Title', 'Category', 'Type', 'Amount']
    ]

    for item in expenses:
        data.append([
            item.date.strftime('%d-%m-%Y'),
            item.title,
            str(item.category) if item.category else '-',
            item.get_transaction_type_display(),
            f"Rs. {item.amount}"
        ])

    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#343a40')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#f2f2f2')]),
    ]))

    elements.append(table)

    pdf.build(elements)

    return response