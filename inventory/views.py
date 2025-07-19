from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from inventory.models import Supplier, Product, Notification, RestockRequest, UserProfile
import os,time
import logging
from django.template.loader import get_template
from io import BytesIO
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.conf import settings
from django.http import FileResponse,JsonResponse
from django.db.models import Count, Sum, Min
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from collections import defaultdict
from django.http import JsonResponse
from django.db.models.functions import TruncMonth
from .forms import UserProductForm
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

# Signup view
def SignUp(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        phone_number = request.POST.get('phone_number', '')
        password = request.POST['password']
        cpassword = request.POST['cpassword']

        if password != cpassword:
            return render(request, 'signup.html', {'error_message': 'Passwords do not match.'})

        # Create the User object
        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password)
        )
        
        # Create the UserProfile for additional data
        UserProfile.objects.create(
            user=user,
            phone_number=phone_number
        )

        return redirect('login1')  # Replace 'login' with your login URL name

    return render(request, 'signup.html')

def register_supplier(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        name = request.POST['name']
        email = request.POST['email']
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')

        if Supplier.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
        elif Supplier.objects.filter(email=email).exists():
            messages.error(request, "Email already used.")
        else:
            supplier = Supplier(
                username=username,
                password=password,  # We will hash it in the model
                name=name,
                email=email,
                phone=phone,
                address=address
            )
            supplier.save()
            messages.success(request, "Registration successful. Please log in.")
            return redirect('login_supplier')  # Redirect to login page after registration

    return render(request, 'supplier/supplier_register.html')

# Login view
def LoginPage(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password1 = request.POST.get('pass')
        user = authenticate(request, username=username, password=password1)
        if user is not None:
            # print("A")
            login(request, user)
            # print("B")
            return redirect('user_dashboard')  # Redirect to product list if preferences exist
        else:
            return HttpResponse("Username or Password incorrect!")
    return render(request, 'login.html')

def login_supplier(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        try:
            supplier = Supplier.objects.get(username=username)
            if check_password(password, supplier.password):  # Check hashed password
                # Store the supplier id in session
                request.session['supplier_id'] = supplier.id
                messages.success(request, "Login successful.")
                return redirect('supplier_dashboard')  # Redirect to supplier dashboard
            else:
                messages.error(request, "Invalid credentials.")
        except Supplier.DoesNotExist:
            messages.error(request, "Invalid credentials.")

    return render(request, 'supplier/supplier_login.html')


# Logout view
def LogoutPage(request):
    logout(request)
    return redirect('login1')

def home(request):
    return render(request, 'home.html')

def product_list(request):
    products = Product.objects.all()  # Fetch all products from the database
    return render(request, 'inventory/product_list.html', {'products': products})  # Render the template with products

@login_required
def user_dashboard(request):
    # Example query to get data from the database
    products_count = Product.objects.count()  # Get the number of products
    orders_count = RestockRequest.objects.count()  # Get the number of orders
    suppliers_count = Supplier.objects.count()  # Get the number of suppliers

    context = {
        'products_count': products_count,
        'orders_count': orders_count,
        'suppliers_count': suppliers_count,
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def user_notifications(request):
    # Get the user profile
    
    # Query notifications related to the user profile
    notifications = Notification.objects.filter(resolved=False)
    return render(request, 'notification.html', {'notifications': notifications})

@login_required
def mark_notification_resolved(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    notification.resolved = True
    notification.save()
    return redirect('user_notifications')

@login_required
def low_stock(request):
    # Fetch low stock notifications for the logged-in user
    notifications = Notification.objects.filter(resolved=False)

    # Get the product IDs from the notifications
    product_ids = notifications.values_list('product_id', flat=True)
    
    # Fetch products that correspond to these notification IDs
    products = Product.objects.filter(id__in=product_ids)

    # Group products by their supplier
    products_by_supplier = defaultdict(list)
    for product in products:
        if product.supplier:  # Check if the product has an associated supplier
            products_by_supplier[product.supplier.name].append(product)

    return render(request, 'inventory/low_stock.html', {
        'products_by_supplier': dict(products_by_supplier),
    })

@login_required
def send_restock_request(request):
    action = request.POST.get('action')
    product_ids = request.POST.getlist('products')

    if action == 'select_all':
        notifications = Notification.objects.filter(resolved=False)
        products = Product.objects.filter(id__in=notifications.values_list('product_id', flat=True))
    else:
        products = Product.objects.filter(id__in=product_ids)

    restock_requests = []

    for product in products:
        if product.supplier is None:
            continue
        
        quantity = 10  # Example fixed quantity, replace with dynamic input if needed
        
        # Create restock request and save the user who is sending the request
        restock_request = RestockRequest.objects.create(
            product=product,
            supplier=product.supplier,
            quantity=quantity,
            is_auto_restock=(action == 'select_all'),
            status='Pending',
        )

        restock_requests.append(restock_request)

    session_key = f'restock_requests_{request.user.id}'
    request.session[session_key] = [r.id for r in restock_requests] 

    return redirect('low_stock')

@login_required
def supplier_requests(request):
    # Fetch restock requests for the logged-in supplier
    supplier = get_object_or_404(Supplier, user=request.user)
    restock_requests = RestockRequest.objects.filter(supplier=supplier, status='Pending')

    return render(request, 'supplier/requests.html', {
        'restock_requests': restock_requests
    })

@login_required
def supplier_dashboard(request):
    # Ensure the supplier is logged in
    supplier_id = request.session.get('supplier_id')
    if not supplier_id:
        messages.error(request, "Please log in to access the dashboard.")
        return redirect('login_supplier')

    try:
        # Retrieve the supplier based on the session's supplier_id
        supplier = Supplier.objects.get(id=supplier_id)
    except Supplier.DoesNotExist:
        messages.error(request, "Supplier profile not found.")
        return redirect('login_supplier')

    # Retrieve all restock requests related to the supplier
    restock_requests = RestockRequest.objects.filter(supplier=supplier)

    # Group restock requests by customer and by status
    restock_requests_by_customer = defaultdict(lambda: {'Pending': [], 'Approved': [], 'Rejected': []})

    for restock_request in restock_requests:
        user = restock_request.user  # Get the associated customer/user
        restock_requests_by_customer[user][restock_request.status].append(restock_request)

    # Dummy data or actual data can be passed
    return render(request, 'supplier/supp_dashboard.html', {
        'supplier': supplier,
        'restock_requests_by_customer': restock_requests_by_customer.items(),
    })

@login_required
def accept_restock_request(request, request_id):
    restock_request = get_object_or_404(RestockRequest, id=request_id)
    supplier = get_object_or_404(Supplier, id=request.session.get('supplier_id'))

    # Check if the restock request belongs to the supplier
    if restock_request.supplier != supplier:
        return redirect('supplier_dashboard')

    restock_request.status = 'Approved'
    restock_request.save()

    return redirect('supplier_dashboard')

@login_required
def reject_restock_request(request, request_id):
    restock_request = get_object_or_404(RestockRequest, id=request_id)
    supplier = get_object_or_404(Supplier, id=request.session.get('supplier_id'))

    # Check if the restock request belongs to the supplier
    if restock_request.supplier != supplier:
        return redirect('supplier_dashboard')

    restock_request.status = 'Rejected'
    restock_request.save()

    return redirect('supplier_dashboard')


@login_required
def add_product(request):
    # Fetch all products from the Product model
    existing_products = Product.objects.all()
    
    if request.method == 'POST':
        form = UserProductForm(request.POST)
        if form.is_valid():
            user_product = form.save()  # Save the new product
            
            # Fetch the updated list of products after adding the new entry
            updated_products = Product.objects.all()
            
            return render(request, 'inventory/product_list.html', {
                'products': updated_products,  # Pass the updated products to the template
            })
    else:
        form = UserProductForm()
    
    # Display the form along with the existing products
    return render(request, 'inventory/add_product.html', {
        'form': form,
        'existing_products': existing_products  # Pass the existing products to the template
    })

@login_required
def update_product(request, product_id):
    # Fetch the product by id, no longer filtering by user
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = UserProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = UserProductForm(instance=product)
    
    return render(request, 'inventory/update_product.html', {'form': form})

@login_required
def delete_product(request, product_id):
    # Fetch the product by id, no longer filtering by user
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product.delete()
        return redirect('product_list')
    
    return render(request, 'inventory/delete_product.html', {'product': product})


def ajax_search(request):
    query = request.GET.get('query', '')

    if query:
        products = Product.objects.filter(product_name__icontains=query)
        restock_requests = RestockRequest.objects.filter(product__product_name__icontains=query)

        product_data = [
            {
                "id": product.id,
                "product_name": product.product_name,
                "stock_quantity": product.stock_quantity,
                "price": product.price,
                "description": product.description,
                "image": product.image.url if product.image else ""  # <- key line
            }
            for product in products
        ]

        restock_data = [
            {
                "id": r.id,
                "product_name": r.product.product_name,
                "quantity": r.quantity
            }
            for r in restock_requests
        ]
    else:
        product_data = []
        restock_data = []

    return JsonResponse({
        'products': product_data,
        'restock_requests': restock_data
    })



def restock_management(request):
    restock_requests = RestockRequest.objects.all()
    return render(request, 'inventory/orders.html', {'restock_requests': restock_requests})

def supplier_management(request):

    suppliers = Supplier.objects.all()  

    return render(request, 'inventory/supplier_management.html', {'suppliers': suppliers})

from django.db.models import Sum

@login_required
def generate_bill(request):
    # Get all accepted restock requests
    restock_requests = RestockRequest.objects.filter(status='Approved')

    # Initialize total cost
    total_cost = 0

    # Prepare the bill data
    bill_data = []

    for restock_request in restock_requests:
        product = restock_request.product
        supplier = restock_request.supplier

        # Calculate the total cost for this product in the request
        product_cost = product.price * restock_request.quantity
        total_cost += product_cost

        # Add the details to the bill data
        bill_data.append({
            'product_name': product.product_name,
            'supplier_name': supplier.name,
            'quantity': restock_request.quantity,
            'unit_price': product.price,
            'total_cost': product_cost,
            'supplier_email': supplier.email,
            'supplier_address': supplier.address,
        })

    # Render the bill template with the data
    return render(request, 'supplier/bill_template.html', {
        'bill_data': bill_data,
        'total_cost': total_cost,
    })
from django.http import JsonResponse
from django.db.models import Sum, F
from django.utils.timezone import now
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from collections import defaultdict

def sales_graph_data(request):
    """Get monthly sales data for the last 12 months"""
    try:
        from store.models import Purchased_item
        
        today = now().date()
        data = {}
        
        # Start from 12 months ago
        start_date = today.replace(day=1) - relativedelta(months=11)
        
        for i in range(12):
            # Calculate month start and end
            month_date = start_date + relativedelta(months=i)
            month_start = month_date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
            
            # Create label
            label = month_date.strftime("%b %Y")
            
            # Calculate total sales for this month
            total_sales = Purchased_item.objects.filter(
                order__date_ordered__range=[month_start, month_end]
            ).aggregate(total=Sum('price'))['total'] or 0
            
            data[label] = float(total_sales)
        
        return JsonResponse({
            "labels": list(data.keys()),
            "sales": list(data.values())
        })
        
    except ImportError:
        return JsonResponse({
            "labels": [],
            "sales": []
        })

def abc_classification_data(request):
    """ABC classification based on sales volume"""
    try:
        from store.models import Purchased_item
        
        # Aggregate sales by product
        sales_data = defaultdict(float)
        
        # Remove the problematic select_related and use the correct fields
        for item in Purchased_item.objects.select_related('user', 'order'):
            # Use item name directly since 'product' field doesn't exist
            product_name = getattr(item, 'name', f'Item {item.id}')
            item_total = float(item.price * item.quantity) if hasattr(item, 'quantity') else float(item.price)
            sales_data[product_name] += item_total
        
        if not sales_data:
            return JsonResponse({
                "percentages": [0, 0, 0],
                "labels": ["A Items", "B Items", "C Items"]
            })
        
        # Sort by total sales (descending)
        sorted_data = sorted(sales_data.items(), key=lambda x: x[1], reverse=True)
        total_sales = sum(val for _, val in sorted_data)
        
        a_count, b_count, c_count = 0, 0, 0
        cumulative_sales = 0
        
        for product, value in sorted_data:
            cumulative_sales += value
            cumulative_percent = (cumulative_sales / total_sales) * 100
            
            if cumulative_percent <= 70:
                a_count += 1
            elif cumulative_percent <= 90:
                b_count += 1
            else:
                c_count += 1
        
        return JsonResponse({
            "percentages": [a_count, b_count, c_count],
            "labels": ["A Items (70%)", "B Items (20%)", "C Items (10%)"]
        })
        
    except ImportError:
        return JsonResponse({
            "percentages": [0, 0, 0],
            "labels": ["A Items", "B Items", "C Items"]
        })

def top_products_data(request):
    """Get top 5 products by sales"""
    try:
        from store.models import Purchased_item
        
        sales_data = defaultdict(float)
        
        # Remove the problematic select_related and use correct fields
        for item in Purchased_item.objects.select_related('user', 'order'):
            product_name = getattr(item, 'name', f'Item {item.id}')
            item_total = float(item.price * item.quantity) if hasattr(item, 'quantity') else float(item.price)
            sales_data[product_name] += item_total
        
        # Get top 5 products
        top_items = sorted(sales_data.items(), key=lambda x: x[1], reverse=True)[:5]
        
        if not top_items:
            return JsonResponse({
                "labels": ["No Data"],
                "sales": [0]
            })
        
        labels = [name for name, _ in top_items]
        values = [round(sales, 2) for _, sales in top_items]
        
        return JsonResponse({
            "labels": labels,
            "sales": values
        })
        
    except ImportError:
        return JsonResponse({
            "labels": ["No Data"],
            "sales": [0]
        })

def low_stock_products(request):
    """Get products with stock below minimum threshold"""
    try:
        from inventory.models import Product
        
        products = Product.objects.filter(
            stock_quantity__lte=F('minimum_stock_threshold')
        ).order_by('stock_quantity')[:10]  # Limit to 10 for better visualization
        
        data = []
        for product in products:
            data.append({
                "name": product.product_name,
                "quantity": product.stock_quantity,
                "threshold": product.minimum_stock_threshold,
                "percentage": round((product.stock_quantity / product.minimum_stock_threshold * 100), 2) if product.minimum_stock_threshold > 0 else 0
            })
        
        return JsonResponse({"low_stock": data})
        
    except ImportError:
        return JsonResponse({"low_stock": []})

def dashboard_counts(request):
    """Get dashboard summary counts"""
    data = {}
    
    # Get product count
    try:
        from inventory.models import Product
        data["total_products"] = Product.objects.count()
    except ImportError:
        data["total_products"] = 0
    
    # Get order counts and total sales amount
    try:
        from store.models import FullOrder, Purchased_item
        
        data["total_orders"] = FullOrder.objects.count()
        # Remove status filter since FullOrder doesn't have a status field
        data["pending_orders"] = 0  # Set to 0 or implement different logic
        
        # Calculate total sales amount from FullOrder
        total_amount = FullOrder.objects.aggregate(Sum('amount'))['amount__sum']
        data["total_sales"] = float(total_amount) if total_amount is not None else 0
        
    except ImportError:
        data["total_orders"] = 0
        data["pending_orders"] = 0
        data["total_sales"] = 0
    
    # Add supplier count if model exists
    try:
        from inventory.models import Supplier
        data["total_suppliers"] = Supplier.objects.count()
    except ImportError:
        data["total_suppliers"] = 0
    
    # Add restock count if model exists
    try:
        from inventory.models import RestockRequest
        data["total_restocks"] = RestockRequest.objects.filter(status='Pending').count()
    except ImportError:
        data["total_restocks"] = 0
    
    return JsonResponse(data)
