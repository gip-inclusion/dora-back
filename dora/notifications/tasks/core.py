import abc

from dora.notifications.enums import NotificationStatus, TaskType
from dora.notifications.models import Notification

"""
Tasks:
    Les tâches de notification étendent cette classe, et doivent implémenter les fonctions :
        - `task_type` : le tag qui permet de rattacher les notifications en base à un type de tâche,
        - `candidates` : retourne un `queryset` contenant la liste des objets concernés par la tâche,
        - `should_trigger` : contient l'implémentation de la planification de la tâche,
        - `process` : enrobe l'action à effectuer si une notification est déclenchée.

    `run` effectue principalement 3 opérations :
        - marquage des notifications obsolètes : pour les objets qui ne sont plus des "candidats",
        - création des nouvelles notifications : en vérifiant si il existe toujours une
          notification en attente pour les objets candidat concernés,
        - vérification du déclenchement des notifications et lancement de l'action associée.

    Il est possible d'enregistrer les classes de tâche via `register` pour que la management command
    `process_notification_tasks` la prenne automatiquement en compte.
"""


class TaskError(Exception):
    pass


class Task(abc.ABC):
    _registered_tasks = set()

    @classmethod
    @abc.abstractmethod
    def task_type(cls) -> TaskType:
        # type de la tâche : déclaré dans `enums.TaskType`
        pass

    @classmethod
    @abc.abstractmethod
    def candidates(cls) -> list:
        # liste des objets concernés par cette tâche de notification
        pass

    @classmethod
    @abc.abstractmethod
    def should_trigger(cls, notification: Notification) -> bool:
        # indique si cette notification doit être déclenchée (code)
        pass

    @classmethod
    @abc.abstractmethod
    def process(
        cls, notification: Notification, strict=True, dry_run=False
    ) -> tuple[int, int]:
        # précise quelle est l'action à effectuer pour un type de notification donné
        #  - `strict`: lève une exception à la première erreur de traitement (par défaut)
        #  - `dry_run`: un tour pour pour rien
        # retourne le nombre de notifications correctement traitées, en erreur et obsolètes
        pass

    def __init__(self, limit=None, *args, **kwargs):
        # mise en cache
        self._candidates = self.candidates()

        # le type de l'objet à récupérer est déduit du nom de la FK
        model_key = f"owner_{self._candidates.model.__name__}_id".lower()

        if model_key not in Notification.__dict__:
            raise TaskError(
                f"Le champ '{model_key}' n'existe pas dans le modèle de notification"
            )

        # liste des objets déjà rattachés à une notification
        already_created_pks = (
            Notification.objects.pending()
            .filter(task_type=self.task_type())
            .values_list(model_key, flat=True)
        )
        already_created = self._candidates.filter(pk__in=already_created_pks)

        # liste des objets plus concernés par une notification
        self._obsolete = already_created.difference(self._candidates)

        # liste des objets pour lesquels une notification doit être créée
        self._to_create = self._candidates.difference(already_created)

    def _check(self, notification: Notification) -> Notification:
        # permet, au besoin, de vérifier l'état de la notification avant traitement
        if not notification:
            raise TaskError("Notification invalide")

        if notification.task_type != self.task_type():
            raise TaskError(
                f"Type de notification incompatible : {notification.task_type}"
            )

        if not notification.is_pending:
            raise TaskError(
                f"Cette notification n'est pas en attente de traitement : {notification}"
            )

        ...

        return notification

    def _new_notification(cls, owner) -> Notification:
        if not owner:
            raise TaskError("Pas de propriétaire défini")

        n = Notification(task_type=cls.task_type())
        owner_field = f"owner_{type(owner).__name__}".lower()

        if not hasattr(n, owner_field):
            raise TaskError(
                f"Le modèle de notification n'a pas de champ nommé '{owner_field}'"
            )

        setattr(n, owner_field, owner)

        return n

    def run(
        self, *, strict=True, dry_run=False, limit=None, **kwargs
    ) -> tuple[int, int, int]:
        if limit is not None:
            if not isinstance(limit, int):
                raise TaskError("'limit' doit être entier")

        if not dry_run:
            # traitement des notifications obsolètes
            if self._obsolete:
                self._obsolete.update(status=NotificationStatus.COMPLETE)

            # création des nouvelles notifications
            if self._to_create:
                Notification.objects.bulk_create(
                    [self._new_notification(obj) for obj in self._to_create]
                )

        # traitement des notification actives et en attente
        errors = ok = 0

        # ordonnées par date de maj en cas d'utilisation de la limite
        notifications = (
            Notification.objects.pending()
            .filter(task_type=self.task_type())
            .order_by("updated_at")
        )
        notifications = notifications[:limit] if limit else notifications

        for n in notifications:
            if self.should_trigger(n):
                try:
                    if not dry_run:
                        self.process(self._check(n))
                except Exception as ex:
                    if strict:
                        raise TaskError(
                            f"Erreur d'exécution de l'action pour :{n}"
                        ) from ex
                    errors += 1
                else:
                    n.trigger()
                    ok += 1

        # traitées correctement, en erreur, obsolètes / ancien objet candidat sorti du scope
        return ok, errors, len(self._obsolete)

    @classmethod
    def register(cls, class_):
        if not (class_ and issubclass(class_, Task)):
            raise TaskError("Impossible d'enregistrer cette classe")

        cls._registered_tasks.add(class_)

    @classmethod
    def unregister(cls, class_):
        if not class_ or class_ not in cls._registered_tasks:
            raise TaskError("Impossible de retirer cette classe")

        cls._registered_tasks.remove(class_)

    @classmethod
    def registered(cls) -> set["Task"]:
        return cls._registered_tasks
