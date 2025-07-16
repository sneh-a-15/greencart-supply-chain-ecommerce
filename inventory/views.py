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
def low_stock_products(request):
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

    return redirect('low_stock_products')

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
        # Example: Search products by name and filter restock requests
        products = Product.objects.filter(product_name__icontains=query)
        restock_requests = RestockRequest.objects.filter(product__product_name__icontains=query)

        product_data = [{"id": product.id, "product_name": product.product_name, "stock_quantity": product.stock_quantity, "price":product.price, "image_url":product.image_url} for product in products]
        restock_data = [{"id": request.id, "product_name": request.product.product_name, "quantity": request.quantity} for request in restock_requests]
    else:
        product_data = []
        restock_data = []

    # Return JSON response
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

