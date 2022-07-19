from django.core.exceptions import ValidationError


def extract_subcategories(service):
    return [s.get("value") for s in service.subcategories.values()]


def extract_categories(service):
    return [s.get("value") for s in service.categories.values()]


def unlink_services_from_category(ServiceCategory, Service, slug):
    """
    Retire la thématique de tous les services
    """
    category = get_category_by_slug(ServiceCategory, slug)
    if category is None:
        raise ValidationError(f"Aucune thématique trouvé avec le slug '{slug}'")

    for service in Service.objects.all():
        categories = extract_categories(service)

        if slug in categories:
            new_categories_ids = [
                s.get("id")
                for s in service.categories.values()
                if s.get("value") != slug
            ]
            new_categories_ids.append(category.id)

            Service.objects.filter(pk=service.pk).first().categories.set(
                list(set(new_categories_ids))
            )


def unlink_services_from_subcategory(ServiceSubCategory, Service, slug):
    """
    Retire le besoin de tous les services
    """
    subcategory = get_subcategory_by_slug(ServiceSubCategory, slug)

    if subcategory is None:
        raise ValidationError(f"Aucun besoin trouvé avec le slug: '{slug}'")

    for service in Service.objects.all():
        sub_categories = extract_subcategories(service)

        if slug in sub_categories:
            new_subcategories_ids = [
                s.get("id")
                for s in service.subcategories.values()
                if s.get("value") != slug
            ]
            new_subcategories_ids.append(subcategory.id)

            Service.objects.filter(pk=service.pk).first().subcategories.set(
                list(set(new_subcategories_ids))
            )


def add_categories_and_subcategories_if_subcategory(
    ServiceCategory,
    ServiceSubCategory,
    Service,
    categories_slug_to_add,
    subcategory_slugs_to_add,
    if_subcategory_slug,
):
    """
    Si le service a le besoin `if_subcategory_slug`, alors :
        - On lui ajoute toutes les thématiques dans `categories_slug_to_add`
        - On lui ajoute toutes les besoins dans `subcategory_slugs_to_add`
    """
    # On vérifie si toutes les thématiques existent
    categories_to_add_ids = []
    for category_slug in categories_slug_to_add:
        category = get_category_by_slug(ServiceCategory, category_slug)
        if category is None:
            raise ValidationError(
                f"Aucune thématique trouvé avec le slug '{category_slug}'"
            )
        categories_to_add_ids.append(category.id)

    # On vérifie si tous les besoins existent
    subcategories_to_add_ids = []
    for subcategory_slug in subcategory_slugs_to_add:
        subcategory = get_subcategory_by_slug(ServiceSubCategory, subcategory_slug)
        if subcategory is None:
            raise ValidationError(
                f"Aucun besoin trouvé avec le slug: '{subcategory_slug}'"
            )
        subcategories_to_add_ids.append(subcategory.id)

    for service in Service.objects.all():
        sub_categories = extract_subcategories(service)

        if if_subcategory_slug in sub_categories:
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


def create_category(ServiceCategory, slug, label):
    ServiceCategory.objects.create(value=slug, label=label)


def get_subcategory_by_slug(ServiceSubCategory, slug):
    return ServiceSubCategory.objects.filter(value=slug).first()


def get_category_by_slug(ServiceCategory, slug):
    return ServiceCategory.objects.filter(value=slug).first()


def create_subcategory(ServiceSubCategory, slug, label):
    ServiceSubCategory.objects.create(value=slug, label=label)


def update_subcategory_slug(ServiceSubCategory, old_slug, new_slug):
    old_subcategory = get_subcategory_by_slug(ServiceSubCategory, old_slug)
    if old_subcategory is None:
        raise ValidationError(f"Aucun besoin trouvé avec le slug: '{old_slug}'")

    new_subcategory = get_subcategory_by_slug(ServiceSubCategory, new_slug)
    if new_subcategory is not None:
        raise ValidationError(f"Le slug '{new_slug}' est déjà utilisé")

    old_subcategory.value = new_slug
    old_subcategory.save()


def update_subcategory_label(ServiceSubCategory, slug, new_label):
    old_subcategory = get_subcategory_by_slug(ServiceSubCategory, slug)
    if old_subcategory is None:
        raise ValidationError(f"Aucun besoin trouvé avec le slug: '{slug}'")

    old_subcategory.label = new_label
    old_subcategory.save()


def replace_subcategory(ServiceSubCategory, Service, from_slug, to_slug):
    """
    Met à jour tous les services en :
        - retirant le besoin `from_slug`
        - ajoutant le besoin `to_slug`
    """
    from_subcategory = get_subcategory_by_slug(ServiceSubCategory, from_slug)
    if from_subcategory is None:
        raise ValidationError(f"Aucun besoin trouvé avec le slug: '{from_slug}'")

    to_subcategory = get_subcategory_by_slug(ServiceSubCategory, to_slug)
    if to_subcategory is None:
        raise ValidationError(f"Aucun besoin trouvé avec le slug: '{to_slug}'")

    for service in Service.objects.all():
        sub_categories = extract_subcategories(service)

        if from_slug in sub_categories:
            new_subcategories_ids = [
                s.get("id")
                for s in service.subcategories.values()
                if s.get("value") != from_slug
            ]
            new_subcategories_ids.append(to_subcategory.id)

            Service.objects.filter(pk=service.pk).first().subcategories.set(
                list(set(new_subcategories_ids)),
            )


def delete_subcategory(ServiceSubCategory, slug):
    """
    Supprime le besoin de la base de données
    """
    subcategory = get_subcategory_by_slug(ServiceSubCategory, slug)
    if subcategory is None:
        raise ValidationError(
            f"Suppression impossible : le besoin '{slug}' n'existe pas"
        )
    subcategory.delete()


def delete_category(ServiceCategory, slug):
    """
    Supprime la thématique de la base de données
    """
    category = get_category_by_slug(ServiceCategory, slug)
    if category is None:
        raise ValidationError(
            f"Suppression impossible: la thématique '{slug}' n'existe pas"
        )
    category.delete()
