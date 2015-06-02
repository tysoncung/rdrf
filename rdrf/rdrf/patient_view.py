from django.shortcuts import render_to_response, RequestContext, redirect
from django.views.generic.base import View
from django.views.generic import CreateView
from django.core.urlresolvers import reverse
from django.forms.formsets import formset_factory
from django.utils.datastructures import SortedDict

from rdrf.models import RegistryForm
from rdrf.models import Registry

from django.forms.models import inlineformset_factory

from registry.patients.models import Patient, PatientAddress, PatientDoctor, Doctor
from registry.patients.admin_forms import PatientForm, PatientAddressForm, PatientDoctorForm

import logging

logger = logging.getLogger("registry_log")


class PatientView(View):

    def get(self, request, registry_code):
        context = {
            'registry_code': registry_code,
            'access': False
        }

        try:
            registry = Registry.objects.get(code=registry_code)
            context['splash_screen'] = registry.patient_splash_screen
        except Registry.DoesNotExist:
            context['error_msg'] = "Registry does not exist"
            logger.error("Registry %s does not exist" % registry_code)
            return render_to_response('rdrf_cdes/patient.html', context, context_instance=RequestContext(request))

        if request.user.is_authenticated():
            try:
                registry = Registry.objects.get(code=registry_code)
                if registry in request.user.registry.all():
                    context['access'] = True
                    context['splash_screen'] = registry.patient_splash_screen
            except Registry.DoesNotExist:
                context['error_msg'] = "Registry does not exist"
                logger.error("Registry %s does not exist" % registry_code)

            try:
                forms = registry.forms

                class FormLink(object):
                    def __init__(self, form):
                        self.form = form
                        patient = Patient.objects.get(user=request.user)
                        self.link = form.link(patient)

                context['forms'] = [FormLink(form) for form in forms]
            except RegistryForm.DoesNotExist:
                logger.error("No questionnaire for %s registry" % registry_code)

            if request.user.is_patient:
                try:
                    patient = Patient.objects.get(user__id=request.user.id)
                    context['patient_record'] = patient
                    context['patient_form'] = PatientForm(instance=patient, user=request.user)
                    context['patient_id'] = patient.id
                except Patient.DoesNotExist:
                    logger.error("Paient record not found for user %s" % request.user.username)

        return render_to_response('rdrf_cdes/patient.html', context, context_instance=RequestContext(request))


class PatientMixin(object):
    model = Patient

    def get_context_data(self, **kwargs):
        kwargs.update({'object_name': 'Patient'})
        return kwargs


class PatientFormMixin(PatientMixin):
    original_form_class = PatientForm
    template_name = 'rdrf_cdes/generic_patient.html'

    def __init__(self, *args, **kwargs):
        super(PatientFormMixin, self).__init__(*args, **kwargs)
        self.user = None   # filled in via get or post
        self.registry_model = None
        self.patient_form = None # created via get_form
        self.patient_model = None



    # common methods
    def _get_registry_specific_fields(self, user, registry_model):
        """
        :param user:
        :param registry_model:
        :return: list of cde_model, field_object pairs
        """
        if not registry_model in user.registry.all():
            return []
        else:
            return registry_model.patient_fields

    def get_form_class(self):
        form_class = self._create_registry_specific_patient_form_class(self.user,
                                                                       self.original_form_class,
                                                                       self.registry_model)
        logger.debug("created form class OK")
        return form_class

    def _set_registry_model(self, registry_code):
        self.registry_model = Registry.objects.get(code=registry_code)
        logger.debug("set registry model to %s" % self.registry_model)

    def get_success_url(self):
        """
        After a successful add where to go?
        Returns the supplied success URL. (We override to redirect to edit screen for the newly added patient)
        """
        registry_code = self.registry_model.code
        patient_id = self.object.pk
        patient_edit_url = reverse('patient_edit', args=[registry_code, patient_id])
        return patient_edit_url

    def set_patient_model(self, patient_model):
        self.patient_model = patient_model

    def _set_user(self, request):
        self.user = request.user
        logger.debug("set user to %s" % self.user)

    def _create_registry_specific_patient_form_class(self, user, form_class, registry_model):
        logger.debug("creating registry specific patient form ...")
        additional_fields = SortedDict()
        field_pairs = self._get_registry_specific_fields(user, registry_model)
        if not field_pairs:
            logger.debug("no registry specific fields - returning original form class")
            return form_class

        for cde, field_object in field_pairs:
            additional_fields[cde.code] = field_object
            logger.debug("adding new field %s" % cde.name)

        new_form_class = type(form_class.__name__, (form_class,), additional_fields)
        logger.debug("returning new form class")
        return new_form_class

    def _get_registry_specific_section_fields(self, user, registry_model):
        field_pairs = self._get_registry_specific_fields(user, registry_model)
        fieldset_title = "%s Specific Fields" % registry_model.code.upper()
        field_list = [pair[0].code for pair in field_pairs]
        return fieldset_title, field_list

    def get_form(self, form_class):
        """
        Returns an instance of the form to be used in this view.
        """
        form_instance = super(PatientFormMixin, self).get_form(form_class)
        self.patient_form = form_instance
        return form_instance

    def get_context_data(self, **kwargs):
        logger.debug("in get_context_data ..")
        # modify kwargs which is passed to render_to_response function

        # context = {
        #     "forms": form_sections,
        #     "patient": patient,
        #     "registry_code": registry_code
        # }
        #
        # return render_to_response('rdrf_cdes/patient_edit.html', context, context_instance=RequestContext(request))

        patient_id = self._get_patient_id()
        patient, forms = self._get_forms(patient_id,
                                         self.registry_model.code,
                                         self.request,
                                         self.patient_form)

        kwargs["forms"] = forms
        kwargs["patient"] = patient
        kwargs["errors"] = any([not form[0].is_valid() for form in forms])
        kwargs["error_messages"] = self._extract_error_messages(forms)
        kwargs["registry_code"] = self.registry_model.code
        kwargs["context_instance"] = RequestContext(self.request)
        logger.debug("updated kwargs = %s" % kwargs)
        return kwargs

    def _extract_error_messages(self, form_pairs):
        # forms is a list of (form, field_info_list) pairs
        error_messages = []
        for form, info in form_pairs:
            if not form.is_valid():
                for error in form.errors:
                    error_messages.append(form.errors[error])
        return error_messages

    def _get_patient_id(self):
        if self.object:
            return self.object.pk
        else:
            return None

    def _get_forms(self,
                   patient_id,
                   registry_code,
                   request,
                   patient_form=None,
                   patient_address_form=None,
                   patient_doctor_form=None):

        user = request.user
        if patient_id is None:
            patient = None
        else:
            patient = Patient.objects.get(id=patient_id)

        registry = Registry.objects.get(code=registry_code)

        if not patient_form:
            if not registry.patient_fields:
                patient_form = PatientForm(instance=patient, user=user, registry_model=registry)
            else:
                munged_patient_form_class = self._create_registry_specific_patient_form_class(user,
                                                                                              PatientForm,
                                                                                              registry)
                patient_form = munged_patient_form_class(instance=patient, user=user, registry_model=registry)

        patient_form.user = user

        if not patient_address_form:
            patient_address = PatientAddress.objects.filter(patient=patient).values()
            patient_address_formset = inlineformset_factory(Patient,
                                                            PatientAddress,
                                                            form=PatientAddressForm,
                                                            extra=0,
                                                            can_delete=True)

            patient_address_form = patient_address_formset(instance=patient, prefix="patient_address")

        personal_details_fields = ('Personal Details', [
            "family_name",
            "given_names",
            "maiden_name",
            "umrn",
            "date_of_birth",
            "place_of_birth",
            "country_of_birth",
            "ethnic_origin",
            "sex",
            "home_phone",
            "mobile_phone",
            "work_phone",
            "email",
        ])

        next_of_kin = ("Next of Kin", [
            "next_of_kin_family_name",
             "next_of_kin_given_names",
             "next_of_kin_relationship",
             "next_of_kin_address",
             "next_of_kin_suburb",
             "next_of_kin_state",
             "next_of_kin_postcode",
             "next_of_kin_home_phone",
             "next_of_kin_mobile_phone",
             "next_of_kin_work_phone",
             "next_of_kin_email",
             "next_of_kin_parent_place_of_birth"
        ])

        rdrf_registry = ("Registry", [
            "rdrf_registry",
            "working_groups",
            "clinician"
        ])

        patient_address_section = ("Patient Address", None)

        # first get all the consents ( which could be different per registry -
        # _and_ per applicability conditions )
        # then add the remaining sections which are fixed
        patient_section_info = patient_form.get_all_consent_section_info(patient, registry_code)
        patient_section_info.extend([rdrf_registry, personal_details_fields, next_of_kin])

        registry_specific_section_fields = self._get_registry_specific_section_fields(user, registry)
        patient_section_info.append(registry_specific_section_fields)


        form_sections = [
            (
                patient_form,
                patient_section_info
            ),
            (
                patient_address_form,
                (patient_address_section,)
            )
        ]

        if registry.get_metadata_item("patient_form_doctors"):
            if not patient_doctor_form:
                patient_doctor = PatientDoctor.objects.filter(patient=patient).values()
                patient_doctor_formset = inlineformset_factory(Patient, Patient.doctors.through,
                                                               form=PatientDoctorForm,
                                                               extra=0,
                                                               can_delete=True)

                patient_doctor_form = patient_doctor_formset(instance=patient, prefix="patient_doctor")

            patient_doctor_section = ("Patient Doctor", None)

            form_sections.append((
                patient_doctor_form,
                (patient_doctor_section,)
            ))

        return patient, form_sections


    def get_form_kwargs(self):
        kwargs = super(PatientFormMixin, self).get_form_kwargs()
        kwargs["user"] = self.request.user    #NB This means we must be mixed in with a View ( which we are)
        kwargs["registry_model"] = self.registry_model
        logger.debug("get form kwargs = %s" % kwargs)
        return kwargs

    def form_valid(self, form):
        logger.debug("form is valid!")
        return super(PatientFormMixin, self).form_valid(form)

    def form_invalid(self, form):
        logger.debug("form is invalid!")
        if form.is_bound:
            logger.debug('form is bound')
        else:
            logger.debug("form is unbound")

        for error in form.errors:
            logger.debug("Error in %s: %s" % (error, form.errors[error]))

        return super(PatientFormMixin, self).form_invalid(form)


class AddPatientView(PatientFormMixin, CreateView):
    success_url = '/'
    model = Patient
    form_class = PatientForm
    template_name = 'rdrf_cdes/generic_patient.html'

    def get(self, request, registry_code):
        if not request.user.is_authenticated():
            patient_add_url = reverse('patient_add', args=[registry_code])
            login_url = reverse('login')
            return redirect("%s?next=%s" % (login_url, patient_add_url))

        self._set_registry_model(registry_code)
        self._set_user(request)

        _, form_sections = self._get_forms(None, registry_code, request)

        context = {
            "forms": form_sections,
            "patient": None,
            "registry_code": registry_code
        }

        return render_to_response('rdrf_cdes/generic_patient.html', context, context_instance=RequestContext(request))

    def post(self, request, registry_code):
        logger.debug("starting POST of Add Patient")
        self._set_user(request)
        self._set_registry_model(registry_code)
        return super(AddPatientView, self).post(request, registry_code)


class PatientEditView(View):

    def get(self, request, registry_code, patient_id):
        if not request.user.is_authenticated():
            patient_edit_url = reverse('patient_edit', args=[registry_code, patient_id,])
            login_url = reverse('login')
            return redirect("%s?next=%s" % (login_url, patient_edit_url))
    
        patient, form_sections = self._get_forms(patient_id, registry_code, request)

        context = {
            "forms": form_sections,
            "patient": patient,
            "registry_code": registry_code
        }
    
        return render_to_response('rdrf_cdes/patient_edit.html', context, context_instance=RequestContext(request))

    def post(self, request, registry_code, patient_id):
        user = request.user
        patient = Patient.objects.get(id=patient_id)
        registry = Registry.objects.get(code=registry_code)


        if registry.patient_fields:
            patient_form_class = self._create_registry_specific_patient_form_class(user,
                                                                                   PatientForm,
                                                                                   registry)

        else:
            patient_form_class = PatientForm

        patient_form = patient_form_class(request.POST, instance=patient, user = request.user)

        patient_address_form_set = inlineformset_factory(Patient, PatientAddress, form=PatientAddressForm)
        address_to_save = patient_address_form_set(request.POST, instance=patient, prefix="patient_address")

        valid_forms = [patient_form.is_valid(), address_to_save.is_valid()]
        
        if registry.get_metadata_item("patient_form_doctors"):
            patient_doctor_form_set = inlineformset_factory(Patient, PatientDoctor, form=PatientDoctorForm)
            doctors_to_save = patient_doctor_form_set(request.POST, instance=patient, prefix="patient_doctor")
            valid_forms.append(doctors_to_save.is_valid())

        if all(valid_forms):
            if registry.get_metadata_item("patient_form_doctors"):
                docs = doctors_to_save.save()
            address_to_save.save()
            patient_instance = patient_form.save()
            self._save_registry_specific_data_in_mongo(patient_instance, registry, request.POST)

            patient, form_sections = self._get_forms(patient_id, registry_code, request)

            context = {
                "forms": form_sections,
                "patient": patient,
                "message": "Patient's details saved successfully"
            }
        else:
            if not registry.get_metadata_item("patient_form_doctors"):
                doctors_to_save = None
            patient, form_sections = self._get_forms(patient_id,
                                                     registry_code,
                                                     request,
                                                     patient_form,
                                                     address_to_save,
                                                     doctors_to_save)
            
            context = {
                "forms": form_sections,
                "patient": patient,
                "errors": True
            }
            
        context["registry_code"] = registry_code
        return render_to_response('rdrf_cdes/patient_edit.html', context, context_instance=RequestContext(request))

    def _get_forms(self,
                   patient_id,
                   registry_code,
                   request,
                   patient_form=None,
                   patient_address_form=None,
                   patient_doctor_form=None):

        user = request.user
        if patient_id is None:
            patient = None
        else:
            patient = Patient.objects.get(id=patient_id)

        registry = Registry.objects.get(code=registry_code)
    
        if not patient_form:
            if not registry.patient_fields:
                patient_form = PatientForm(instance=patient, user=user)
            else:
                munged_patient_form_class = self._create_registry_specific_patient_form_class(user,
                                                                                              PatientForm,
                                                                                              registry)
                patient_form = munged_patient_form_class(instance=patient, user=user)

        if not patient_address_form:
            patient_address = PatientAddress.objects.filter(patient=patient).values()
            patient_address_formset = inlineformset_factory(Patient,
                                                            PatientAddress,
                                                            form=PatientAddressForm,
                                                            extra=0,
                                                            can_delete=True)

            patient_address_form = patient_address_formset(instance=patient, prefix="patient_address")

        personal_details_fields = ('Personal Details', [
            "family_name",
            "given_names",
            "maiden_name",
            "umrn",
            "date_of_birth",
            "place_of_birth",
            "country_of_birth",
            "ethnic_origin",
            "sex",
            "home_phone",
            "mobile_phone",
            "work_phone",
            "email",
        ])
        
        next_of_kin = ("Next of Kin", [
            "next_of_kin_family_name",
             "next_of_kin_given_names",
             "next_of_kin_relationship",
             "next_of_kin_address",
             "next_of_kin_suburb",
             "next_of_kin_state",
             "next_of_kin_postcode",
             "next_of_kin_home_phone",
             "next_of_kin_mobile_phone",
             "next_of_kin_work_phone",
             "next_of_kin_email",
             "next_of_kin_parent_place_of_birth"
        ])

        rdrf_registry = ("Registry", [
            "rdrf_registry",
            "working_groups",
            "clinician"
        ])

        patient_address_section = ("Patient Address", None)

        # first get all the consents ( which could be different per registry -
        # _and_ per applicability conditions )
        # then add the remaining sections which are fixed
        patient_section_info = patient_form.get_all_consent_section_info(patient, registry_code)
        patient_section_info.extend([rdrf_registry, personal_details_fields, next_of_kin])

        registry_specific_section_fields = self._get_registry_specific_section_fields(user, registry)
        patient_section_info.append(registry_specific_section_fields)

        
        form_sections = [
            (
                patient_form,
                patient_section_info
            ),
            (
                patient_address_form, 
                (patient_address_section,)
            )
        ]

        if registry.get_metadata_item("patient_form_doctors"):
            if not patient_doctor_form:
                patient_doctor = PatientDoctor.objects.filter(patient=patient).values()
                patient_doctor_formset = inlineformset_factory(Patient, Patient.doctors.through,
                                                               form=PatientDoctorForm,
                                                               extra=0,
                                                               can_delete=True)

                patient_doctor_form = patient_doctor_formset(instance=patient, prefix="patient_doctor")
    
            patient_doctor_section = ("Patient Doctor", None)
            
            form_sections.append((
                patient_doctor_form,
                (patient_doctor_section,)
            ))
                
        return patient, form_sections

    def _get_registry_specific_fields(self, user, registry_model):
        """
        :param user:
        :param registry_model:
        :return: list of cde_model, field_object pairs
        """
        if not registry_model in user.registry.all():
            return []
        else:
            return registry_model.patient_fields

    def _create_registry_specific_patient_form_class(self, user, form_class, registry_model):
        additional_fields = SortedDict()
        field_pairs = self._get_registry_specific_fields(user, registry_model)

        for cde, field_object in field_pairs:
            additional_fields[cde.code] = field_object

        new_form_class = type(form_class.__name__, (form_class,), additional_fields)
        return new_form_class

    def _get_registry_specific_section_fields(self, user, registry_model):
        field_pairs = self._get_registry_specific_fields(user, registry_model)
        fieldset_title = "%s Specific Fields" % registry_model.code.upper()
        field_list = [pair[0].code for pair in field_pairs]
        return fieldset_title, field_list

    def _save_registry_specific_data_in_mongo(self, patient_model, registry, post_data):
        from rdrf.dynamic_data import DynamicDataWrapper
        if registry.patient_fields:
            mongo_patient_data = {registry.code: {}}
            for cde, field_object in registry.patient_fields:
                cde_code = cde.code
                field_value = post_data[cde.code]
                mongo_patient_data[registry.code][cde_code] = field_value
            mongo_wrapper = DynamicDataWrapper(patient_model)
            mongo_wrapper.save_registry_specific_data(mongo_patient_data)
