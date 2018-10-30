import sys
import time
import logging
import datetime

from django.db import transaction
from django.utils import timezone

from framework.celery_tasks import app as celery_app
from website.app import setup_django
setup_django()
from osf.models import Session

from scripts.utils import add_file_logger

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


SESSION_AGE_THRESHOLD = 30


def main(dry_run=True):
    old_sessions = Session.objects.filter(modified__lt=timezone.now() - datetime.timedelta(days=SESSION_AGE_THRESHOLD))

    if dry_run:
        logger.warn('Dry run mode, will delete sessions and then abort the transaction')
    logger.info('Preparing to delete Session objects older than {} days'.format(SESSION_AGE_THRESHOLD))

    with transaction.atomic():
        start = time.time()
        sessions_deleted = old_sessions.delete()[1]['osf.Session']
        end = time.time()

        logger.info('Deleting {} Session objects took {} seconds'.format(sessions_deleted, end - start))

        if dry_run:
            raise Exception('Dry run, aborting the transaction!')


@celery_app.task(name='scripts.clear_sessions')
def run_main(dry_run=True):
    if not dry_run:
        add_file_logger(logger, __file__)
    main(dry_run=dry_run)


if __name__ == '__main__':
    run_main(dry_run='--dry' in sys.argv)
