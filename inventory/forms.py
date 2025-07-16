from django import forms
from inventory.models import Product

class UserProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['product_name', 'price', 'stock_quantity', 'image_url', 'supplier']
        widgets = {
            'product_name': forms.TextInput(attrs={'class': 'form-input'}),
            'price': forms.NumberInput(attrs={'class': 'form-input'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-input'}),
            'image_url': forms.URLInput(attrs={'class': 'form-input'}),
            'supplier': forms.Select(attrs={'class': 'form-input'}),
        }