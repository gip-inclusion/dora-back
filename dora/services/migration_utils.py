from django.core.exceptions import ValidationError


def extract_subcategories(service):
    return [s["value"] for s in service.subcategories.values()]


def extract_categories(service):
    return [s["value"] for s in service.categories.values()]


def unlink_services_from_category(ServiceCategory, Service, value):
    """
    Retire la thématique de tous les services
    """
    category = get_category_by_value(ServiceCategory, value)
    if category is None:
        raise ValidationError(f"Aucune thématique trouvé avec la value '{value}'")

    services = Service.objects.filter(categories=category)
    for service in services:
        service.categories.remove(category)

    """
    for service in Service.objects.all():
        categories = extract_categories(service)

        if value in categories:
            new_categories_ids = [
                s.get("id")
                for s in service.categories.values()
                if s.get("value") != value
            ]
            new_categories_ids.append(category.id)

            Service.objects.filter(pk=service.pk).first().categories.set(
                list(set(new_categories_ids))
            )
    """


def unlink_services_from_subcategory(ServiceSubCategory, Service, value):
    """
    Retire le besoin de tous les services
    """
    subcategory = get_subcategory_by_value(ServiceSubCategory, value)

    if subcategory is None:
        raise ValidationError(f"Aucun besoin trouvé avec la value: '{value}'")

    services = Service.objects.filter(sub_categories=subcategory)
    for service in services:
        service.sub_categories.remove(subcategory)

    """
    for service in Service.objects.all():
        sub_categories = extract_subcategories(service)

        if value in sub_categories:
            new_subcategories_ids = [
                s.get("id")
                for s in service.subcategories.values()
                if s.get("value") != value
            ]
            new_subcategories_ids.append(subcategory.id)

            Service.objects.filter(pk=service.pk).first().subcategories.set(
                list(set(new_subcategories_ids))
            )
    """


def add_categories_and_subcategories_if_subcategory(
    ServiceCategory,
    ServiceSubCategory,
    Service,
    categories_value_to_add,
    subcategory_value_to_add,
    if_subcategory_value,
):
    """
    Si le service a le besoin `if_subcategory_value`, alors :
        - On lui ajoute toutes les thématiques dans `categories_value_to_add`
        - On lui ajoute toutes les besoins dans `subcategory_value_to_add`
    """
    # On vérifie si toutes les thématiques existent
    categories_to_add_ids = []
    for category_value in categories_value_to_add:
        category = get_category_by_value(ServiceCategory, category_value)
        if category is None:
            raise ValidationError(
                f"Aucune thématique trouvé avec la value '{category_value}'"
            )
        categories_to_add_ids.append(category.id)

    # On vérifie si tous les besoins existent
    subcategories_to_add_ids = []
    for subcategory_value in subcategory_value_to_add:
        subcategory = get_subcategory_by_value(ServiceSubCategory, subcategory_value)
        if subcategory is None:
            raise ValidationError(
                f"Aucun besoin trouvé avec la value: '{subcategory_value}'"
            )
        subcategories_to_add_ids.append(subcategory.id)

    for service in Service.objects.all():
        sub_categories = extract_subcategories(service)

        if if_subcategory_value in sub_categories:
            # Ajout des thématiques
            new_categories_ids = [s.get("id") for s in service.categories.values()]
            for id in categories_to_add_ids:
                new_categories_ids.append(id)

            service.categories.set(list(set(new_categories_ids)))

            # Ajout des besoins
            new_subcategories_ids = [
                s.get("id") for s in service.subcategories.values()
            ]
            for id in subcategories_to_add_ids:
                new_subcategories_ids.append(id)

            service.subcategories.set(list(set(new_subcategories_ids)))

            # Sauvegarde
            Service.objects.filter(pk=service.pk).first().subcategories.set(
                list(set(new_subcategories_ids))
            )
            Service.objects.filter(pk=service.pk).first().categories.set(
                list(set(new_categories_ids))
            )


def create_category(ServiceCategory, value, label):
    ServiceCategory.objects.create(value=value, label=label)


def get_subcategory_by_value(ServiceSubCategory, value):
    return ServiceSubCategory.objects.filter(value=value).first()


def get_category_by_value(ServiceCategory, value):
    return ServiceCategory.objects.filter(value=value).first()


def create_subcategory(ServiceSubCategory, value, label):
    ServiceSubCategory.objects.create(value=value, label=label)


def update_subcategory_value_and_label(
    ServiceSubCategory, old_value, new_value, new_label
):
    old_subcategory = get_subcategory_by_value(ServiceSubCategory, old_value)
    if old_subcategory is None:
        raise ValidationError(f"Aucun besoin trouvé avec la value: '{old_value}'")

    new_subcategory = get_subcategory_by_value(ServiceSubCategory, new_value)
    if new_subcategory is not None:
        raise ValidationError(f"La value '{new_value}' est déjà utilisé")

    old_subcategory.value = new_value
    old_subcategory.label = new_label
    old_subcategory.save()


def replace_subcategory(ServiceSubCategory, Service, from_value, to_value):
    """
    Met à jour tous les services en :
        - retirant le besoin `from_value`
        - ajoutant le besoin `to_value`
    """
    from_subcategory = get_subcategory_by_value(ServiceSubCategory, from_value)
    if from_subcategory is None:
        raise ValidationError(f"Aucun besoin trouvé avec la value: '{from_value}'")

    to_subcategory = get_subcategory_by_value(ServiceSubCategory, to_value)
    if to_subcategory is None:
        raise ValidationError(f"Aucun besoin trouvé avec la value: '{to_value}'")

    for service in Service.objects.all():
        sub_categories = extract_subcategories(service)

        if from_value in sub_categories:
            new_subcategories_ids = [
                s.get("id")
                for s in service.subcategories.values()
                if s.get("value") != from_value
            ]
            new_subcategories_ids.append(to_subcategory.id)

            Service.objects.filter(pk=service.pk).first().subcategories.set(
                list(set(new_subcategories_ids)),
            )


def delete_subcategory(ServiceSubCategory, value):
    """
    Supprime le besoin de la base de données
    """
    subcategory = get_subcategory_by_value(ServiceSubCategory, value)
    if subcategory is None:
        raise ValidationError(
            f"Suppression impossible : le besoin '{value}' n'existe pas"
        )
    subcategory.delete()


def delete_category(ServiceCategory, value):
    """
    Supprime la thématique de la base de données
    """
    category = get_category_by_value(ServiceCategory, value)
    if category is None:
        raise ValidationError(
            f"Suppression impossible: la thématique '{value}' n'existe pas"
        )
    category.delete()
