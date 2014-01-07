from django.db import models
import logging



logger = logging.getLogger("registry")

class Registry(models.Model):
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=10)
    desc = models.TextField()
    splash_screen = models.TextField()

    @property
    def questionnaire(self):
        return RegistryForm.objects.get(registry=self, is_questionnaire=True)
    
    def __unicode__(self):
        return "%s (%s)" % (self.name, self.code)


def get_owner_choices():
    """
    Get choices for CDE owner drop down.
    Used to get the list of classes which CDEs can be attached to.
    UNUSED means this CDE will not be used to construct any forms in the registry.

    """
    from django.conf import settings
    choices = [('UNUSED', 'UNUSED')]
    # for display_name, owner_model_func in settings.CDE_MODEL_MAP.items():
    #     owner_class_name = owner_model_func().__name__
    #     choices.append((owner_class_name, display_name))

    return [("UNUSED","UNUSED"), ("USED", "USED")]

class CDEPermittedValueGroup(models.Model):
    code = models.CharField(max_length=250, primary_key=True)

    def __unicode__(self):
        return "PVG %s" % (self.code)

class CDEPermittedValue(models.Model):
    code = models.CharField(max_length=30, primary_key=True)
    value = models.CharField(max_length=256)
    desc = models.TextField(null=True)
    pv_group = models.ForeignKey(CDEPermittedValueGroup, related_name='permitted_value_set')

    def __unicode__(self):
        return "PV %s:%s of %s" % (self.code,self.value,self.pv_group)

class CommonDataElement(models.Model):
    code = models.CharField(max_length=30, primary_key=True)
    name = models.CharField(max_length=250, blank=False, help_text="Label for field in form")
    desc = models.TextField(blank=True, help_text="origin of field")
    datatype = models.CharField(max_length=50, help_text="type of field")
    instructions = models.TextField(blank=True, help_text="Used to indicate help text for field")
    pv_group = models.ForeignKey(CDEPermittedValueGroup, null=True, blank=True, help_text="If a range, indicate the Permissible Value Group")
    allow_multiple = models.BooleanField(default=False, help_text="If a range, indicate whether multiple selections allowed")
    max_length = models.IntegerField(blank=True,null=True, help_text="Length of field - only used for character fields")
    max_value= models.IntegerField(blank=True, null=True, help_text="Only used for numeric fields")
    min_value= models.IntegerField(blank=True, null=True, help_text="Only used for numeric fields")
    is_required = models.BooleanField(default=False, help_text="Indicate whether field is non-optional")
    pattern = models.CharField(max_length=50, blank=True, help_text="Regular expression to validate string fields (optional)")
    widget_name = models.CharField(max_length=80, blank=True, help_text="If a special widget required indicate here - leave blank otherwise")
    calculation = models.TextField(blank=True, help_text="Calculation in javascript. Use context.CDECODE to refer to other CDEs. Must use context.result to set output")
    questionnaire_text = models.TextField(blank=True, help_text="The text to use in any public facing questionnaires/registration forms")

    def __unicode__(self):
        return "CDE %s:%s" % (self.code, self.name)


class RegistryFormManager(models.Manager):
    def get_by_registry(self, registry):
        return self.model.objects.filter(registry__id__in = registry)

class RegistryForm(models.Model):
    """
    A representation of a form ( a bunch of sections)
    """
    registry = models.ForeignKey(Registry)
    name = models.CharField(max_length=80)
    sections = models.TextField(help_text="Comma-separated list of sections")
    objects = RegistryFormManager()
    is_questionnaire = models.BooleanField(default=False,help_text="Check if this form is questionnaire form for it's registry")

    def __unicode__(self):
        return "%s %s Form comprising %s" % (self.registry, self.name, self.sections)

    def get_sections(self):
        import string
        return map(string.strip,self.sections.split(","))



class Section(models.Model):
    """
    A group of fields that appear on a form as a unit
    """
    code = models.CharField(max_length=50)
    display_name = models.CharField(max_length=100)
    elements = models.TextField()
    allow_multiple = models.BooleanField(default=False, help_text="Allow extra items to be added")
    extra = models.IntegerField(blank=True,null=True, help_text="Extra rows to show if allow_multiple checked")

    def __unicode__(self):
        return "Section %s comprising %s" % (self.code, self.elements)

    def get_elements(self):
        import string
        return map(string.strip,self.elements.split(","))


class Wizard(models.Model):
    registry = models.CharField(max_length=50)
    forms = models.TextField(help_text="A comma-separated list of forms")
    # idea
    # rules for "decision tree"
    # These could be as simple as the following:
    # A wizard is a way of coordinating the asking of questions and evaluating
    # answers -

    #  E.g. in pseudo-code ( we either present a gui to create rules like this
    # or write an interpreter
    #  present form1.
    #  if form1.section1.cde2 == 3 and section2.cde >6  then present form3
    #  if form1.section2.cde2 == 4 then present form5
    #  else present form6
    #
    rules = models.TextField(help_text="Rules")


class QuestionnaireResponse(models.Model):
    registry = models.ForeignKey(Registry)
    date_submitted = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    patient_id = models.IntegerField(blank=True,null=True,help_text="The id of the patient created from this response, if any")












