
from django.utils.translation import ugettext_lazy as _


REGISTER_WARNING = _('Registration cannot be undone, and the archived content and files cannot '
                     'be deleted after registration. Please be sure the project is complete and '
                     'comprehensive for what you wish to register. Post to new URL to continue.')

EMBARGO_INFORMATION = _('You can choose whether to make your registration public immediately or embargo '
                        'it for up to four years. At the end of the embargo period the registration is '
                        'automatically made public. After becoming public, the only way to remove a '
                        'registration is to retract it. Retractions show only the registration title, '
                        'contributors, and description to indicate that a registration was made and '
                        'later retracted.  If you choose to embargo your registration, a notification'
                        ' will be sent to all other project contributors. Other administrators will have'
                        ' 48 hours to approve or cancel creating the registration. If any other '
                        'administrator rejects the registration, it will be canceled. If all other '
                        'administrators approve or do nothing, the registration will be confirmed and '
                        'enter its embargo period.')