# orders/migrations/000X_backfill_orderitem_cost_price.py
from django.db import migrations
from django.db.models import F, OuterRef, Subquery

def populate_cost_price(apps, schema_editor):
    """
    Updates OrderItem.cost_price based on the current Product.cost_price
    for items where cost_price is currently NULL.
    """
    OrderItem = apps.get_model('orders', 'OrderItem')
    Product = apps.get_model('inventory', 'Product')
    db_alias = schema_editor.connection.alias

    # Subquery to get the product's current cost_price
    product_cost_subquery = Product.objects.filter(pk=OuterRef('product_id')).values('cost_price')[:1]

    # Update OrderItems where cost_price is NULL and the related product exists
    OrderItem.objects.using(db_alias).filter(
        cost_price__isnull=True,
        product_id__isnull=False # Ensure product link exists
    ).update(
        cost_price=Subquery(product_cost_subquery)
    )
    # Optional: Update items where product exists but product has no cost price? Set to 0?
    # OrderItem.objects.using(db_alias).filter(
    #     cost_price__isnull=True,
    #     product_id__isnull=False,
    #     product__cost_price__isnull=True # If product cost is NULL
    # ).update(cost_price=0)


def reverse_populate_cost_price(apps, schema_editor):
    """ Optional: How to reverse the migration (e.g., set back to NULL) """
    # This might not be perfectly reversible if some items originally had 0 cost
    # OrderItem = apps.get_model('orders', 'OrderItem')
    # db_alias = schema_editor.connection.alias
    # OrderItem.objects.using(db_alias).update(cost_price=None) # Simplistic reversal
    pass # Or just do nothing on reverse


class Migration(migrations.Migration):

    dependencies = [
        # Add dependency on the migration that added the cost_price field
        ('orders', '0003_orderitem_cost_price'), # Adjust migration number if needed
        ('inventory', '0002_product_cost_price_product_manufacturer'), # Dependency on inventory might be needed if not implicitly handled
    ]

    operations = [
        migrations.RunPython(populate_cost_price, reverse_populate_cost_price),
    ]