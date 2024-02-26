from datetime import timedelta

from django.utils.timezone import now

from policy.models import Policy
from policy.services import update_insuree_policies
from product.models import Product
from .apps import AutoenrollConfig

import logging
logger = logging.getLogger("openimis." + __name__)


def autoenroll_family(insuree, family=None):
    if not insuree:
        return
    if not family:
        family = insuree.family
    eligible_products = determine_eligibility_to_autoenrollment(insuree, family)
    for product_code in eligible_products:
        product = get_autoenroll_product(product_code)
        policy, policy_created = get_or_create_policy(insuree, family, product)
        if policy_created:
            logger.info(f"Autoenrolled insuree {insuree.id} into policy {policy.id} - product {product_code}")
        else:
            logger.info(f"Insuree {insuree.id} already autoenrolled into policy {policy.id} - product {product_code}")


def determine_eligibility_to_autoenrollment(insuree, family):
    # Checks whether or not the insuree and family are eligible to products
    eligible_products = set()

    if insuree.age() < 5:
        eligible_products.add(AutoenrollConfig.autoenroll_product_minors)
    elif insuree.age() >= 65:
        eligible_products.add(AutoenrollConfig.autoenroll_product_elderly)

    if family.poverty:
        eligible_products.add(AutoenrollConfig.autoenroll_product_indigents)
    # hasattr so that there is no crash for insuree.is_pregnant if this custom dev doesn't exist on the instance
    if hasattr(insuree, "is_pregnant") and insuree.is_pregnant:
        eligible_products.add(AutoenrollConfig.autoenroll_product_pregnant_women)

    return eligible_products


def get_autoenroll_product(code):
    """
    Autoenroll needs to know which product to create, this gets product configured into the app.
    """
    try:
        return Product.objects.get(code=code, validity_to__isnull=True)
    except Product.DoesNotExist:
        logger.error(f"Autoenroll product {code} not found")
        raise


def get_or_create_policy(insuree, family, product):
    """
    Check for the existence (and active status) of a policy for the given insuree and product.
    If it doesn't exist, create it.
    """
    if insuree.age() < 5 and product.code == AutoenrollConfig.autoenroll_product_minors:
        expiry_date = insuree.dob + timedelta(days=365 * 5)  # Policy until their 5th birthday
    elif insuree.age() >= 65 and product.code == AutoenrollConfig.autoenroll_product_elderly:
        expiry_date = insuree.dob + timedelta(days=365 * 125)  # Policy until their 125th birthday
    else:
        expiry_date = now() + timedelta(days=365 * product.insurance_period)  # Otherwise we simply take the standard duration

    policy, policy_created = Policy.objects.get_or_create(
        validity_to=None,
        product=product,
        family=family,
        status=Policy.STATUS_ACTIVE,
        defaults=dict(
            stage=Policy.STAGE_NEW,
            expiry_date=expiry_date,
            enroll_date=now(),  # TODO use the registration date if available
            start_date=now(),  # TODO use the registration date if available
            effective_date=now(),
            value=0,
            audit_user_id=-1,
        )
    )
    update_insuree_policies(policy, -1)
    if policy_created:
        logger.debug(f"Created policy {policy.id} for insuree {insuree.id}")
    return policy, policy_created
