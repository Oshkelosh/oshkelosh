from app.models import models
import importlib
import json

from app.utils.logging import get_logger

log = get_logger(__file__)

def sync_products():
    addon_list = models.Addon.get(type='SUPPLIER')
    for supplier in addon_list:
        config = models.Config(addon_id=supplier.id)
        data = config.data()

        try:
            module_path = f'app.addons.suppliers.{supplier.name}'
            module = importlib.import_module(module_path)
            sync_function = getattr(module, 'sync_product')
            base_products = []
            variant_products = []
            product_data = sync_function(data)
            for base in product_data:
                variants = base.pop("variants")
                variant_products.extend(variants)
                base_products.append(base)
            product_list = []
            product_list.extend(base_products)
            product_list.extend(variant_products)
            print(json.dumps(product_list, indent=4))
            check_products(product_list, supplier.id)

        except ImportError as e:
            log.warning(f"Failed importing supplier addon {supplier.name}: {e}")
        except AttributeError:
            log.warning(f"Supplier addon {supplier.name} missing 'sync_product' function")
        except Exception as e:
            log.error(f"Error running sync_products for supplier addon {supplier.name}: {e}")


def check_products(product_data, supplier_id):
    if not product_data:
        return
    try:
        for product in product_data:
            images = []
            if "images" in product:
                images = product.pop("images")
            db_product = models.Product.get(product_id = product["product_id"])
            if not db_product:
                if not product["is_base"]:
                    print(json.dumps(product, indent=4))
                    base_product_id = product.pop('base_product_id')
                    base_product = models.Product.get(product_id=base_product_id)
                    product["variant_of_id"] = base_product[0].id
                db_product = models.Product.new(**product)
            else:
                db_product = db_product[0]
            
            if not db_product.active:
                db_product.active = True
                db_product.update()

            if images:
                check_images(images, db_product.id)

        db_products = models.Product.get(supplier_id=supplier_id)
        for product in db_products:
            if product.product_id not in [product_info["product_id"] for product_info in product_data]:
                product.active = False
                product.update()
    except Exception as e:
        log.error(f"Exception during check_products: {e}")
        raise

def check_images(image_list, product_id):
    if not image_list:
        return
    try:
        for image in image_list:
            db_image = models.Image.get(image_id = image["image_id"])
            if not db_image:
                db_image = models.Image.new(**image, product_id=product_id)
    except Exception as e:
        log.error(f"Exception during check_images: {e}")
        raise
