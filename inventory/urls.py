from django.contrib import admin
from django.urls import path
import inventory.views as view1

urlpatterns = [
# ---------------- inventory urls here ------------------

    # path('admin/', admin.site.urls),
    path('home/', view1.home, name='home'),
    path('signup/', view1.SignUp, name='signup'),
    path('login1/', view1.LoginPage, name='login1'),
    path('logout/', view1.LogoutPage, name='logout'),
    path('dashboard/', view1.user_dashboard, name='user_dashboard'),
    path('products/', view1.product_list, name='product_list'), 
    path('notifications/', view1.user_notifications, name='user_notifications'),
    path('notifications/mark-resolved/<int:notification_id>/', view1.mark_notification_resolved, name='mark_notification_resolved'),
    # path('out-of-stock/', view1.out_of_stock_products, name='out_of_stock_products'),
    path('low-stock/', view1.low_stock_products, name='low_stock_products'),
    path('send-restock-requests/', view1.send_restock_request, name='send_restock_request'),
    path('supplier_dashboard/',view1.supplier_dashboard, name='supplier_dashboard'),
    path('login_supplier',view1.login_supplier,name="login_supplier"),
    path('register_supplier',view1.register_supplier,name="register_supplier"),
    # path('download_pdf/',view1.download_pdf,name='download_pdf'),
    path('products/add/', view1.add_product, name='add_product'),
    path('products/update/<int:product_id>/', view1.update_product, name='update_product'),
    path('products/delete/<int:product_id>/', view1.delete_product, name='delete_product'),
    path('supplier/request/accept/<int:request_id>/', view1.accept_restock_request, name='accept_restock_request'),
    path('supplier/request/reject/<int:request_id>/', view1.reject_restock_request, name='reject_restock_request'),
    path('ajax/search/', view1.ajax_search, name='ajax_search'), 
    path('order-management/', view1.restock_management, name='restock_management'),
    path('supplier_management/', view1.supplier_management, name='supplier_management'),
    path('generate_bill/', view1.generate_bill, name='generate_bill'),
]