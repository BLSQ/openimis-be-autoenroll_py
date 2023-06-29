import random

from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core.management.base import BaseCommand
from django.db.models import Q, OuterRef, Exists

from ...services import get_autoenroll_product, get_or_create_policy
from insuree.models import Insuree, InsureePolicy


class Command(BaseCommand):
    help = "This command will search through the database for insurees <5 or >=65 without a policy and create one"

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            dest='verbose',
            help='Be verbose about what it is doing',
        )

    def handle(self, *args, **options):
        less_than_five_date = today() - relativedelta(years=5)
        over_65_date = today() - relativedelta(years=65)
        product = get_autoenroll_product()
        has_active_policy = InsureePolicy.objects.filter(
            validity_to__isnull=True,
            policy__product=product,
            policy__validity_to__isnull=True,
            insuree_id=OuterRef("id"),
        )

        query = Insuree.objects\
            .annotate(has_active_policy=Exists(has_active_policy))\
            .filter(
                (Q(dob__gt=less_than_five_date) | Q(dob__lte=over_65_date)) &
                Q(validity_to__isnull=True) &
                Q(has_active_policy=False)
            ).prefetch_related("family")

        for insuree in query:
            policy, policy_created = get_or_create_policy(insuree, insuree.family, product)
            if options["verbose"]:
                if policy_created:
                    self.stdout.write(f"Autoenrolled insuree {insuree.id} into policy {policy.id}")
                else:
                    self.stdout.write(f"Insuree {insuree.id} already autoenrolled into policy {policy.id}")