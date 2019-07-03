import sys
from django.core.management import BaseCommand
explanation = "This command creates a Patient Review"


class NoUserException(Exception):
    pass


class UnsupportedReviewType(Exception):
    pass


class NoParentException(Exception):
    pass


class Command(BaseCommand):
    help = 'Create a Patient review'

    def add_arguments(self, parser):
        parser.add_argument('-r', "--registry-code",
                            action='store',
                            dest='registry_code',
                            help='Registry code containing Review')
        parser.add_argument('-rc', '--review-code',
                            action='store',
                            dest='review_code',
                            help='Review code')
        parser.add_argument('-pid', '--patient-id',
                            action='store',
                            dest='patient_id',
                            help='Patient ID')

    def _usage(self):
        print(explanation)

    def _print(self, msg):
        self.stdout.write(msg + "\n")

    def handle(self, *args, **options):
        from registry.patients.models import Patient
        from registry.patients.models import ParentGuardian
        from rdrf.models.definition.models import Registry
        from rdrf.models.definition.review_models import Review
        from rdrf.models.definition.review_models import PatientReview

        def make_review(review_model, registry_model, patient_model):
            try:
                parent = ParentGuardian.objects.get(patient=patient_model)
            except ParentGuardian.DoesNotExist:
                raise NoParentException
            except ParentGuardian.MultipleObjectsReturned:
                # do this for now
                parent = ParentGuardian.objects.filter(patient=patient_model).first()

            default_context = patient_model.default_context(registry_model)
            if review_model.review_type == "R":
                # user is the parent
                user = parent.user
            elif review_model.review_type == "V":
                user = patient_model.clinician
            else:
                raise UnsupportedReviewType

            if user is None:
                raise NoUserException

            pr = PatientReview(review=review_model,
                               patient=patient_model,
                               context=default_context)
            pr.user = user
            pr.parent = parent
            pr.save()
            pr.create_review_items()
            url = "/reviews?t=%s" % pr.token
            code = pr.review.code
            print("review %s patient %s url = %s" % (code,
                                                     patient_model,
                                                     url))

        registry_code = options.get("registry_code", None)
        if registry_code is None:
            self._print("Error: registry code required")
            sys.exit(1)
        try:
            registry_model = Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            self._print("Error: registry does not exist")
            sys.exit(1)

        patient_id = options.get("patient_id", None)
        if patient_id is None:
            all_patients = True
        else:
            all_patients = False

        review_code = options.get("review_code", None)
        if review_code is None:
            self._print("Error: review code required")
            sys.exit(1)

        try:
            review_model = Review.objects.get(registry=registry_model,
                                              code=review_code)
        except Review.DoesNotExist:
            self._print("Error: review does not exist")
            sys.exit(1)

        if all_patients:
            for patient_model in Patient.objects.filter(rdrf_registry__in=[registry_model]):
                try:
                    make_review(review_model,
                                registry_model,
                                patient_model)
                except NoUserException:
                    print("patient %s has no associated user" % patient_model)
                except NoParentException:
                    print("patient %s has no associated parent" % patient_model)
        else:
            try:
                patient_model = Patient.objects.get(id=patient_id)
            except Patient.DoesNotExist:
                print("patient with id %s does not exist" % patient_id)
                sys.exit(1)
            try:
                make_review(review_model,
                            registry_model,
                            patient_model)
            except NoUserException:
                print("patient %s has no associated user" % patient_model)

            except NoParentException:
                print("patient %s has no associated parent" % patient_model)
