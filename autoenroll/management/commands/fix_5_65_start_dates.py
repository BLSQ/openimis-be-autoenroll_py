import logging

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.core.paginator import Paginator

from policy.models import Policy
from product.models import Product


logger = logging.getLogger(__name__)


UPDATE_PAGE_SIZE = 1000

class Command(BaseCommand):
    help = "This command will fix the enrollment date for automatic enrollments of -5 and 65+"

    def add_arguments(self, parser):
        parser.add_argument(
            '--children',
            default="BASIC-5",
            help="Product code for children under 5, by default BASIC-5",
        )
        parser.add_argument(
            '--elderly',
            default="BASIC65+",
            help="Product code for the elderly of 65 or over, by default BASIC65+",
        )

    def handle(self, *args, **options):
        error_message = (
            "This command was created in order to clean data on the GMB production instance after the autoenrollment date bug fix."
            "It was a one shot and should not be used again.")
        print(error_message)
        logger.error(error_message)
        return

        children_code = options["children"]
        children_product = Product.objects.filter(validity_to__isnull=True, code=children_code).first()
        if not children_product:
            logger.error(f"Error - can't fetch product {children_code}")
            return

        elderly_code = options["elderly"]
        elderly_product = Product.objects.filter(validity_to__isnull=True, code=elderly_code).first()
        if not elderly_product:
            logger.error(f"Error - can't fetch product {elderly_code}")
            return

        logger.info("*** Products successfully fetched ***")

        total_children = 0
        total_elderly = 0

        logger.info("*** Starting to update children policies ***")
        children_policies = (Policy.objects.filter(validity_to__isnull=True, product=children_product)
                                           .prefetch_related("family__head_insuree")
                                           .order_by("id"))

        paginator = Paginator(children_policies, UPDATE_PAGE_SIZE)
        for page_number in paginator.page_range:
            page = paginator.page(page_number)

            for children_policy in page.object_list:
                insuree = children_policy.family.head_insuree
                logger.info(f"\t {total_children + 1} - updating policy {children_policy.id} for {insuree.chf_id} ***")
                dob = insuree.dob
                children_policy.enroll_date = dob
                children_policy.start_date = dob
                children_policy.effective_date = dob
                children_policy.save()
                total_children += 1
        logger.info("*** Finished updating children policies ***")

        logger.info("*** Starting to update elderly policies ***")
        elderly_policies = (Policy.objects.filter(validity_to__isnull=True, product=elderly_product)
                                          .prefetch_related("family__head_insuree")
                                          .order_by("id"))

        paginator = Paginator(elderly_policies, UPDATE_PAGE_SIZE)
        for page_number in paginator.page_range:
            page = paginator.page(page_number)

            for elderly_policy in page.object_list:
                insuree = elderly_policy.family.head_insuree
                logger.info(f"\t {total_elderly + 1} - updating policy {elderly_policy.id} for {insuree.chf_id} ***")
                start_date = insuree.dob + relativedelta(years=65)
                elderly_policy.enroll_date = start_date
                elderly_policy.start_date = start_date
                elderly_policy.effective_date = start_date
                elderly_policy.save()
                total_elderly += 1
        logger.info("*** Finished updating elderly policies ***")

        logger.info("*** TOTAL ***")
        logger.info(f"\t - children policies updated: {total_children}")
        logger.info(f"\t - elderly policies updated: {total_elderly}")
        logger.info(f"\t - total policies updated: {total_children + total_elderly}")
