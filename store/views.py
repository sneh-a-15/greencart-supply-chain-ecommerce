from django.shortcuts import render
from .models import OrderItem, ShippingAddress, FullOrder, Purchased_item
from inventory.models import ProductCategories, Product
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, Http404
from django.views.decorators.csrf import csrf_exempt
from .forms import ShippingForm, ShippingUpdateForm
from django.urls import reverse
import datetime

def store(request):
    total_item_cart = 0
    if request.user.is_authenticated:
        items = OrderItem.objects.filter(user=request.user)
        for item in items:
            total_item_cart += item.quantity

    product_categories = ProductCategories.objects.all()

    context = {
        'product_categories': product_categories,
        'total_item_cart': total_item_cart,
    }
    return render(request, 'store/store.html', context)

def checkout(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('user_login'))

    items = []
    total_cost_cart = 0
    total_item_cart = 0

    if request.user.is_authenticated:
        items = OrderItem.objects.filter(user=request.user)
        for item in items:
            total_item_cart += item.quantity
            total_cost_cart += item.get_total

    if total_item_cart == 0:
        return Http404

    form = ShippingForm()
    if request.method == 'POST':
        form = ShippingForm(request.POST)
        if form.is_valid():
            adr = form.save(commit=False)
            adr.user = request.user
            adr.save()
        return HttpResponseRedirect(reverse('checkout'))

    addresses = ShippingAddress.objects.filter(user=request.user)
    product_categories = ProductCategories.objects.all()

    context = {
        'product_categories': product_categories,
        'items': items,
        'total_item_cart': total_item_cart,
        'total_cost_cart': total_cost_cart,
        'form': form,
        'addresses': addresses,
    }
    return render(request, 'store/checkout.html', context)

@csrf_exempt
def insert_into_cart(request):
    total_item_cart = 0
    about = 'item_not_added'
    if request.user.is_authenticated:
        about = 'Item Added'
        product_id = request.POST.get('product_id')
        product = Product.objects.get(id=product_id)
        if OrderItem.objects.filter(product=product, user=request.user).exists():
            item = OrderItem.objects.get(product=product, user=request.user)
            item.quantity += 1
            item.save()
        else:
            item = OrderItem.objects.create(product=product, user=request.user, quantity=1)
            item.save()

        items = OrderItem.objects.filter(user=request.user)
        for item in items:
            total_item_cart += item.quantity

    dic = {
        'data': about,
        'total_item_cart': total_item_cart,
    }
    return JsonResponse(dic, safe=False)

@csrf_exempt
def update_item_quantity(request):
    about = 'Some Error Occurred'
    if request.user.is_authenticated:
        about = 'Item Updated'
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')
        product = Product.objects.get(id=product_id)
        item = OrderItem.objects.get(product=product, user=request.user)

        if action == 'add':
            item.quantity += 1
        else:
            item.quantity -= 1
        item.save()
        if item.quantity <= 0:
            item.delete()

    dic = {
        'data': about,
    }
    return JsonResponse(dic, safe=False)

def cart(request):
    items = []
    total_cost_cart = 0
    total_item_cart = 0

    if request.user.is_authenticated:
        items = OrderItem.objects.filter(user=request.user)
        for item in items:
            total_item_cart += item.quantity
            total_cost_cart += item.get_total

    check = total_item_cart > 0
    product_categories = ProductCategories.objects.all()

    context = {
        'items': items,
        'total_item_cart': total_item_cart,
        'total_cost_cart': total_cost_cart,
        'check': check,
        'product_categories': product_categories,
    }
    return render(request, 'store/cart.html', context)

def item_detail(request, id):
    total_item_cart = 0

    if request.user.is_authenticated:
        items = OrderItem.objects.filter(user=request.user)
        for item in items:
            total_item_cart += item.quantity

    product = Product.objects.get(id=id)
    limited_stock = product.stock_quantity <= product.minimum_stock_threshold
    product_categories = ProductCategories.objects.all()

    context = {
        'product_categories': product_categories,
        'product': product,
        'total_item_cart': total_item_cart,
        'limited_stock': limited_stock,  # Pass the limited_stock variable here
    }

    return render(request, 'store/item_detail.html', context)



def order_details(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('user_login'))

    total_item_cart = 0
    if request.user.is_authenticated:
        items = OrderItem.objects.filter(user=request.user)
        for item in items:
            total_item_cart += item.quantity

    orders = FullOrder.objects.filter(user=request.user).order_by('-date_ordered')

    ordered = []
    for order in orders:
        items = Purchased_item.objects.filter(order=order)
        ordered.append({'order': order, 'items': items})

    product_categories = ProductCategories.objects.all()

    context = {
        'product_categories': product_categories,
        'ordered': ordered,
        'total_item_cart': total_item_cart,
    }
    return render(request, 'store/order_details.html', context)

def make_payment(request, id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('user_login'))

    dt = datetime.datetime.now()
    seq = int(dt.strftime("%Y%m%d%H%M%S"))

    adr = ShippingAddress.objects.get(id=id)
    obj = FullOrder.objects.create(user=request.user)
    obj.recepient_fullname = adr.recepient_fullname
    obj.phone_no = adr.phone_no
    obj.address_line1 = adr.address_line1
    obj.address_line2 = adr.address_line2
    obj.city = adr.city
    obj.state = adr.state
    obj.country = adr.country
    obj.zipcode = adr.zipcode
    obj.transaction_id = seq
    obj.save()

    total_amount = 0
    items = OrderItem.objects.filter(user=request.user)
    limited_stock_warning = False

    for item in items:
        product = item.product
        item_purchased = Purchased_item.objects.create(order=obj)
        item_purchased.user = request.user
        item_purchased.quantity = item.quantity
        item_purchased.name = product.product_name
        item_purchased.price = product.price
        item_purchased.image = product.image
        item_purchased.description = product.description
        item_purchased.save()
        
        total_amount += product.price * item.quantity
        product.stock_quantity -= item.quantity
        product.save()
        print("Stock reduced")

        if product.stock_quantity <= product.minimum_stock_threshold:
            limited_stock_warning = True

        item.delete()

    obj.amount = total_amount
    obj.save()

    context = {
        'limited_stock_warning': limited_stock_warning,
        'total_amount': total_amount,
    }
    
    return render(request, 'store/payment_success.html', context)

def delete_address(request,id):

    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('user_login'))

    adr = ShippingAddress.objects.get(id=id)

    if adr.user != request.user:
        return Http404

    adr.delete()
    return HttpResponseRedirect(reverse('checkout'))


def show_items(request, id):
    total_item_cart = 0

    if request.user.is_authenticated:
        items = OrderItem.objects.filter(user=request.user)
        for item in items:
            total_item_cart += item.quantity

    product_category = ProductCategories.objects.get(id=id)
    products = Product.objects.filter(category=product_category)

    product_categories = ProductCategories.objects.all()

    # Initialize a list to store products with limited stock
    limited_stock_warning = []

    # Loop through each product and check stock quantity
    for product in products:
        if product.stock_quantity <= product.minimum_stock_threshold:
            limited_stock_warning.append(product.id)  # Append product ID to the list if stock is low

    context = {
        'product_categories': product_categories,
        'product_category': product_category,
        'products': products,
        'total_item_cart': total_item_cart,
        'limited_stock_warning': limited_stock_warning,  # Pass the list of products with limited stock
    }

    return render(request, 'store/show_items.html', context)


def search(request):
    total_item_cart = 0

    query = request.GET['search']

    if request.user.is_authenticated:
        items = OrderItem.objects.filter(user=request.user)
        for item in items:
            total_item_cart += item.quantity

    product_categories = ProductCategories.objects.all()
    products_temp = Product.objects.all()

    products =[]

    for p in products_temp:
        if query.lower() in p.name.lower() or query.lower() in p.description.lower():
            products.append(p)

    context = {
        'products' : products,
        'product_categories': product_categories,
        'total_item_cart': total_item_cart,
    }

    return render(request, 'store/search.html', context)


def update_address(request,id):

    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('user_login'))

    total_item_cart = 0
    if request.user.is_authenticated:
        items = OrderItem.objects.filter(user=request.user)
        for item in items:
            total_item_cart += item.quantity

    product_categories = ProductCategories.objects.all()

    adr = ShippingAddress.objects.get(id=id)

    if adr.user != request.user:
        return Http404()

    if request.method == 'POST':
        form = ShippingUpdateForm(request.POST,instance=adr)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('checkout'))
    else:
        form = ShippingUpdateForm(instance=adr)

    context = {
        'product_categories' : product_categories,
        'total_item_cart' : total_item_cart,
        'form' : form ,
    }

    return render(request ,'store/update_address.html',context)