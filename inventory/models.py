from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"

class Supplier(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True)  # Supplier username
    password = models.CharField(max_length=128)  # Hashed password
    name = models.CharField(max_length=255)  # Supplier name
    email = models.EmailField(unique=True)  # Supplier email
    phone = models.CharField(max_length=15, blank=True, null=True)  # Optional phone number
    address = models.TextField(blank=True, null=True)  # Supplier address

    def save(self, *args, **kwargs):
        if not self.pk:  # If the object is being created
            self.password = make_password(self.password)  # Hash the password
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    

class ProductCategories(models.Model):

    name = models.CharField(max_length=100,blank=False,null=True)
    image = models.ImageField(null=True,blank=False)

    @property
    def get_imageURL(self):
        try:
            url = self.image.url
        except:
            url = ''
        return url

    def __str__(self):
        return self.name

    
class Product(models.Model):
    category = models.ManyToManyField(ProductCategories, blank=True)  # Multiple categories
    product_name = models.CharField(max_length=255)  # Product name
    description = models.TextField(blank=True, null=True)  # Optional description
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, related_name='products')  # Supplier link
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Product price
    stock_quantity = models.PositiveIntegerField(default=0)  # Stock quantity
    image = models.ImageField(null=True, blank=True)  # Image for media storage
    image_url = models.URLField(max_length=500, blank=True, null=True)  # Image URL for external sources
    last_sold_date = models.DateTimeField(blank=True, null=True)  # Last sale date
    created_at = models.DateTimeField(auto_now_add=True)  # Creation date
    updated_at = models.DateTimeField(auto_now=True)  # Update date
    minimum_stock_threshold = models.PositiveIntegerField(default=0)  # Threshold for alerts

    def __str__(self):
        return self.product_name

    def check_stock_level(self):
        if self.stock_quantity <= self.minimum_stock_threshold:
            # Trigger notification
            Notification.objects.create(
                product=self,
                message=f"{self.product_name} is low in stock. Please restock."
            )

    @property
    def get_imageURL(self):
        return self.image.url if self.image else self.image_url if self.image_url else ""

# Notification Model using DefaultUser
class Notification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='notifications')  # Link to Product
    message = models.CharField(max_length=255)  # Notification message
    created_at = models.DateTimeField(auto_now_add=True)  # Creation timestamp
    resolved = models.BooleanField(default=False)  # Resolution status

    # def __str__(self):
    #     return f"Notification for {self.user.username}: {self.message}"

# RestockRequest Model 
class RestockRequest(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    quantity = models.IntegerField()  # Restock quantity
    is_auto_restock = models.BooleanField(default=True)  # Auto restock indicator
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Processed', 'Processed')])
    created_at = models.DateTimeField(auto_now_add=True)
    pdf_file_path = models.FileField(upload_to='restock_bills/', null=True, blank=True)
    discount = models.FloatField(default=0.0)  # Discount percentage
    estimated_delivery_date = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='restock_requests')  # Link to DefaultUser

    def __str__(self):
        return f"Restock request for {self.product.product_name} by {self.user.username if self.user else 'Unknown'}"
