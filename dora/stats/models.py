from django.db import models


class DeploymentLevel(models.IntegerChoices):
    NONE = 0, "Aucun contact"
    PENDING = 1, "En cours d'échanges"
    STARTED = 2, "Premières saisies de services"
    IN_PROGRESS = 3, "Déploiement en cours"
    FINALIZING = 4, "Finalisation du déploiement"


class DeploymentState(models.Model):
    department_code = models.CharField(max_length=3, blank=True)
    department_name = models.CharField(max_length=230)
    state = models.IntegerField(
        choices=DeploymentLevel.choices,
        verbose_name="État de déploiement",
        default=DeploymentLevel.NONE,
    )

    class Meta:
        verbose_name = "État de déploiement"
        verbose_name_plural = "État de déploiement"

    def __str__(self):
        return f"{self.department_name} ({self.department_code})"
