from rest_framework import serializers

from .models import SolutionThemes, Structure


class StructureSerializer(serializers.ModelSerializer):
    solutions_themes = serializers.SerializerMethodField()

    class Meta:
        model = Structure
        # Temporary, while working on the exact model content
        fields = "__all__"

    def get_solutions_themes(self, obj):
        def get_choice_label(choices, value):
            return [l for [v, l] in choices if v == value][0]

        return [
            get_choice_label(SolutionThemes.choices, value)
            for value in obj.solutions_themes
        ]
