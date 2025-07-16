import logging
from celery import shared_task
from .models import Product, Notification
from django.db.models import F

# Set up a logger for the task
logger = logging.getLogger(__name__)

@shared_task
def check_and_notify_stock_levels():
    logger.info("Starting check_and_notify_stock_levels task")

    try:
        # Fetch all products that need restocking
        products = Product.objects.filter(stock_quantity__lte=F('minimum_stock_threshold'))
        logger.info(f"Found {products.count()} products that need restocking.")

        for product in products:
            if product.stock_quantity <= product.minimum_stock_threshold:
                # Check if notification already exists for the product
                existing_notification = Notification.objects.filter(
                    product=product,
                    resolved=False  # Optionally, check for unresolved notifications only
                ).first()

                if not existing_notification:
                    # Generate notification for each product that needs restocking for all users
                    Notification.objects.create(
                        product=product,
                        message=f"{product.product_name} is low in stock. Please restock."
                    )
                    logger.info(f"Notification created for {product.product_name} (ID: {product.id}).")
                else:
                    logger.info(f"Notification already exists for {product.product_name} (ID: {product.id}).")

    except Exception as e:
        logger.error(f"Error occurred while checking stock levels: {str(e)}")

    logger.info("check_and_notify_stock_levels task completed.")
