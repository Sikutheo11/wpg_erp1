from rest_framework import serializers
from construction.models import Project


class ProjectBudgetSerializer(serializers.ModelSerializer):
    spent = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    remaining = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'budget', 'spent', 'remaining']

    def get_remaining(self, obj):
        return obj.budget - obj.total_spent