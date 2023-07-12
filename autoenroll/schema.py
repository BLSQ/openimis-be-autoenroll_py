from autoenroll.services import autoenroll_family
from core.models import MutationLog
from core.schema import signal_mutation_module_after_mutating
from insuree.models import Insuree, Family

import logging

from policy.models import Policy, PolicyMutation
from policy.services import update_insuree_policies

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
    mutation = MutationLog.objects.filter(client_mutation_id=mutation_args['data']['client_mutation_id']).first()
    if not mutation or not mutation.policies.first():
        return []

    try:
        policy = mutation.policies.first().policy
        if policy.value == 0 and policy.status == Policy.STATUS_IDLE:
            policy.enroll_date = policy.start_date
            policy.status = Policy.STATUS_ACTIVE
            policy.save()
            update_insuree_policies(policy, -1)

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
    }.get(sender._mutation_class, lambda x: [])(kwargs)


def bind_signals():
    signal_mutation_module_after_mutating["insuree"].connect(after_mutation)
    signal_mutation_module_after_mutating["policy"].connect(after_mutation)


