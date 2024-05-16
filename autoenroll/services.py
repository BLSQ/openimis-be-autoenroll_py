from datetime import timedelta

from dateutil.relativedelta import relativedelta
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
    eligible_product_codes = determine_eligibility_to_autoenrollment(insuree, family)
    for product_code in eligible_product_codes:
        product = get_autoenroll_product(product_code)
        policy, policy_created = get_or_create_policy(insuree, family, product)
        if policy_created:
            logger.info(f"Autoenrolled insuree {insuree.id} into policy {policy.id} - product {product_code}")
        else:
            logger.info(f"Insuree {insuree.id} already autoenrolled into policy {policy.id} - product {product_code}")


def determine_eligibility_to_autoenrollment(insuree, family):
    # Checks whether or not the insuree and family are eligible to products
    eligible_product_codes = set()

    if insuree.age() < 5:
        eligible_product_codes.add(AutoenrollConfig.autoenroll_product_minors)
    elif insuree.age() >= 65:
        eligible_product_codes.add(AutoenrollConfig.autoenroll_product_elderly)

    if family.poverty:
        eligible_product_codes.add(AutoenrollConfig.autoenroll_product_indigents)
    # hasattr so that there is no crash for insuree.is_pregnant if this custom dev doesn't exist on the instance
    if hasattr(insuree, "is_pregnant") and insuree.is_pregnant:
        eligible_product_codes.add(AutoenrollConfig.autoenroll_product_pregnant_women)

    return eligible_product_codes


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
    current_time = now()
    if insuree.age() < 5 and product.code == AutoenrollConfig.autoenroll_product_minors:
        expiry_date = insuree.dob + relativedelta(years=5) - relativedelta(days=1)  # Policy until their 5th birthday
    elif insuree.age() >= 65 and product.code == AutoenrollConfig.autoenroll_product_elderly:
        expiry_date = insuree.dob + relativedelta(years=125)  # Policy until their 125th birthday
    else:
        # Otherwise we simply take the standard product duration
        expiry_date = current_time + relativedelta(months=product.insurance_period) - relativedelta(days=1)

    policy, policy_created = Policy.objects.get_or_create(
        validity_to=None,
        product=product,
        family=family,
        status=Policy.STATUS_ACTIVE,
        defaults=dict(
            stage=Policy.STAGE_NEW,
            expiry_date=expiry_date,
            enroll_date=current_time,  # TODO use the registration date if available
            start_date=current_time,  # TODO use the registration date if available
            effective_date=current_time,
            value=0,
            audit_user_id=-1,
        )
    )
    update_insuree_policies(policy, -1)
    if policy_created:
        logger.debug(f"Created policy {policy.id} for insuree {insuree.id}")
    return policy, policy_created


def activate_policy_if_free_and_idle(policy: Policy):
    if policy.value == 0 and policy.status == Policy.STATUS_IDLE:
        policy.enroll_date = policy.start_date
        policy.effective_date = policy.start_date
        policy.status = Policy.STATUS_ACTIVE
        policy.save()
        update_insuree_policies(policy, -1)
