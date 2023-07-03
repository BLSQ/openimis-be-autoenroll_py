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
    if is_family_eligible_for_autoenroll(insuree):
        product = get_autoenroll_product()
        policy, policy_created = get_or_create_policy(insuree, family, product)
        if policy_created:
            logger.info(f"Autoenrolled insuree {insuree.id} into policy {policy.id}")
        else:
            logger.info(f"Insuree {insuree.id} already autoenrolled into policy {policy.id}")


def is_family_eligible_for_autoenroll(insuree):
    """
    In this unconditional autoenroll, we just return True.
    """
    return True


def get_autoenroll_product():
    """
    Autoenroll needs to know which product to create, this gets product configured into the app.
    """
    try:
        return Product.objects.get(code=AutoenrollConfig.autoenroll_product_code, validity_to__isnull=True)
    except Product.DoesNotExist:
        logger.error(f"Autoenroll product {AutoenrollConfig.autoenroll_product_code} not found")
        raise


def get_or_create_policy(insuree, family, product):
    """
    Check for the existence (and active status) of a policy for the given insuree and product.
    If it doesn't exist, create it.
    """
    expiry_date = now() + timedelta(days=365 * 5)  # unconditionally enroll for 5 years

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
            value=0,
            audit_user_id=-1,
        )
    )
    update_insuree_policies(policy, -1)
    if policy_created:
        logger.debug(f"Created policy {policy.id} for insuree {insuree.id}")
    return policy, policy_created
