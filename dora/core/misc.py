from collections import OrderedDict

from django.utils.encoding import force_str
from rest_framework.metadata import SimpleMetadata

# When getting metadata for a model, we want to see the available options
# for related fields, so we need to revert https://github.com/encode/django-rest-framework/pull/4021
# This is a probably a temporary fix only, as in many cases that's not what we'll want.


class RelatedMetadata(SimpleMetadata):
    def get_field_info(self, field):
        """
        Given an instance of a serializer field, return a dictionary
        of metadata about it.
        """
        field_info = OrderedDict()
        field_info["type"] = self.label_lookup[field]
        field_info["required"] = getattr(field, "required", False)

        attrs = [
            "read_only",
            "label",
            "help_text",
            "min_length",
            "max_length",
            "min_value",
            "max_value",
        ]

        for attr in attrs:
            value = getattr(field, attr, None)
            if value is not None and value != "":
                field_info[attr] = force_str(value, strings_only=True)

        if getattr(field, "child", None):
            field_info["child"] = self.get_field_info(field.child)
        elif getattr(field, "fields", None):
            field_info["children"] = self.get_serializer_info(field)

        if (
            not field_info.get("read_only")
            # and not isinstance(
            #     field, (serializers.RelatedField, serializers.ManyRelatedField)
            # )
            and hasattr(field, "choices")
        ):
            field_info["choices"] = [
                {
                    "value": choice_value,
                    "label": force_str(choice_name, strings_only=True),
                }
                for choice_value, choice_name in field.choices.items()
            ]

        return field_info
