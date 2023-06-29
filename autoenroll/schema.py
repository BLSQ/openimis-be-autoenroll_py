from autoenroll.services import autoenroll_family
from core.schema import signal_mutation_module_after_mutating
from insuree.models import Insuree, Family

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


def after_family_mutation(sender, **kwargs):
    return {
        "CreateFamilyMutation": lambda x: on_family_mutation(x),
        "UpdateFamilyMutation": lambda x: on_family_mutation(x),
        "CreateInsureeMutation": lambda x: on_insuree_mutation(x),
        "UpdateInsureeMutation": lambda x: on_insuree_mutation(x),
    }.get(sender._mutation_class, lambda x: [])(kwargs)


def bind_signals():
    signal_mutation_module_after_mutating["insuree"].connect(after_family_mutation)

