from autoenroll.services import autoenroll_family, activate_policy_if_free_and_idle
from core.models import MutationLog
from core.schema import signal_mutation_module_after_mutating
from insuree.models import Insuree

import logging


logger = logging.getLogger("openimis." + __name__)


def on_family_mutation(mutation_args):
    # This module was created for The Gambia where families only have one member
    head_of_family_chf = mutation_args['data'].get('head_insuree', {}).get('chf_id', None)
    try:
        insuree = Insuree.objects.get(chf_id=head_of_family_chf, validity_to__isnull=True)
        family = insuree.family
        if not family:
            return []
        autoenroll_family(insuree, family)
    except Insuree.DoesNotExist:
        logger.warning(F"Family with head insuree with chf {head_of_family_chf} not found")
    except Exception as e:
        logger.exception("Error occurred during autoenrollment of family")

    return []


def on_insuree_mutation(mutation_args):
    insuree_uuid = mutation_args['data'].get('uuid', {})
    try:
        insuree = Insuree.objects.get(uuid=insuree_uuid, validity_to__isnull=True)
        family = insuree.family
        if not family:
            return []
        autoenroll_family(insuree, family)
    except Insuree.DoesNotExist:
        logger.warning(F"Insuree with uuid {insuree_uuid} not found")
    except Exception as e:
        logger.exception("Error occurred during autoenrollment of insuree")

    return []


def on_policy_mutation(mutation_args):
    # This module was created for The Gambia where families only have one member
    logger.info("on policy mutation triggered")
    mutation_id = mutation_args['data']['client_mutation_id']
    mutation = MutationLog.objects.filter(client_mutation_id=mutation_id).first()
    if not mutation or not mutation.policies.first():
        mutation_id = mutation_args['data']['client_mutation_id']
        logger.info(f"on policy mutation - couldn't find the mutation that was requested {mutation_id}")
        return []

    try:
        logger.info(f"on policy mutation - activating policy")
        policy = mutation.policies.first().policy
        activate_policy_if_free_and_idle(policy)

    except Insuree.DoesNotExist:
        logger.warning(F"Family with head insuree with chf {None} not found")
    except Exception as e:
        logger.exception("Error occurred during autoenrollment of family")

    return []


def on_mobile_mutation(mutation_args):
    logger.info("on mobile mutation triggered")
    mutation_id = mutation_args['data']['client_mutation_id']
    mutation = MutationLog.objects.filter(client_mutation_id=mutation_id).first()
    if not mutation or not mutation.mobile_enrollments.first():
        logger.info(f"on mobile mutation - couldn't find the mutation that was requested {mutation_id}")
        return []

    try:
        logger.info(f"on mobile mutation - activating policy")
        policy = mutation.mobile_enrollments.first().policy
        activate_policy_if_free_and_idle(policy)

    except Insuree.DoesNotExist:
        logger.warning(F"Family with head insuree with chf {None} not found")
    except Exception as e:
        logger.exception("Error occurred during autoenrollment of family")

    return []


def after_mutation(sender, **kwargs):
    return {
        # Family/Insuree mutations
        "CreateFamilyMutation": lambda x: on_family_mutation(x),
        "UpdateFamilyMutation": lambda x: on_family_mutation(x),
        "CreateInsureeMutation": lambda x: on_insuree_mutation(x),
        "UpdateInsureeMutation": lambda x: on_insuree_mutation(x),
        # Policy mutations
        "CreatePolicyMutation": lambda x: on_policy_mutation(x),
        "UpdatePolicyMutation": lambda x: on_policy_mutation(x),
        # Mobile mutations
        "MobileEnrollmentMutation": lambda x: on_mobile_mutation(x),
    }.get(sender._mutation_class, lambda x: [])(kwargs)


def bind_signals():
    signal_mutation_module_after_mutating["insuree"].connect(after_mutation)
    signal_mutation_module_after_mutating["policy"].connect(after_mutation)
    signal_mutation_module_after_mutating["mobile"].connect(after_mutation)
