from unittest.mock import Mock, patch

import pytest
from django.conf import settings
from django.urls import reverse

from dora.core.test_utils import make_structure, make_user
from dora.users.enums import MainActivity


@pytest.mark.parametrize(
    "main_activity,expected_sib_list",
    [
        (MainActivity.OFFREUR, settings.SIB_ONBOARDING_LIST),
        (MainActivity.ACCOMPAGNATEUR, settings.SIB_ONBOARDING_PUTATIVE_MEMBER_LIST),
        (
            MainActivity.ACCOMPAGNATEUR_OFFREUR,
            settings.SIB_ONBOARDING_PUTATIVE_MEMBER_LIST,
        ),
    ],
)
@patch("dora.onboarding._create_or_update_sib_contact")
@patch("dora.onboarding._setup_sib_client", Mock(return_value=True))
def test_onboard_other_activities(
    mock_create_contact, main_activity, expected_sib_list, api_client
):
    # Les utilisateurs ayant offreurs ou autre pour activité principale
    # sont redirigés vers l'ancienne liste Brevo (onboarding "traditionnel").

    # Les utilisateurs accompagnateurs ou accompagnateurs/offreurs
    # sont "onboardés" sur la bonne liste Brevo des invités lors de leur première invitation.

    # note : le deuxième patch n'est pas pris en compte comme un paramètre du test
    # (à cause de l'association directe/explicite à un nouveau mock)

    structure = make_structure()
    # La création d'un admin de la structure est nécessaire pour que l'utilisateur
    # soit rattaché en tant qu'invité (sinon il en devient le premier membre et admin).
    make_user(structure=structure, is_admin=True)
    invited_user = make_user(main_activity=main_activity)

    api_client.force_authenticate(user=invited_user)
    api_client.post(
        reverse("join-structure"),
        data={
            # Utiliser le slug, car le SIRET sera invalide (random).
            "structure_slug": structure.slug,
            "cgu_version": "1",
        },
    )

    assert (
        invited_user in structure.putative_members.all()
    ), "L'utilisateur n'est pas un invité de la structure"
    assert mock_create_contact.called, "Le contact Brevo n'a pas été créé"

    _, user, attrs, sib_list = mock_create_contact.call_args.args

    assert user == invited_user, "L'utilisateur ne correspond pas"
    assert attrs, "Les attributs Brevo ne sont pas définis"
    assert str(sib_list) == expected_sib_list


@pytest.mark.parametrize(
    "main_activity,expected_sib_list",
    [
        (MainActivity.ACCOMPAGNATEUR, settings.SIB_ONBOARDING_MEMBER_LIST),
        (MainActivity.ACCOMPAGNATEUR_OFFREUR, settings.SIB_ONBOARDING_MEMBER_LIST),
    ],
)
@patch("dora.onboarding._create_or_update_sib_contact")
@patch("dora.onboarding._setup_sib_client", Mock(return_value=True))
def test_onboard_new_member(
    mock_create_contact, main_activity, expected_sib_list, api_client
):
    # Les utilisateurs accompagnateurs ou accompagnateurs/offreurs
    # sont "onboardés" sur la liste Brevo des membres lors de leur premier rattachement à une structure.

    member = make_user(main_activity=main_activity)
    structure = make_structure(putative_member=member)
    admin = make_user(structure=structure, is_admin=True)

    # Cette action doit-être effectuée par un admin de la structure.
    api_client.force_authenticate(user=admin)

    # L'utilisateur accepte l'invitation.
    r = api_client.post(
        reverse(
            "structure-putative-member-accept-membership-request",
            kwargs={"pk": structure.putative_membership.first().pk},
        ),
    )

    # Etant différent du traditionnel 200, on teste le statut de retour.
    assert 201 == r.status_code, "Code de status invalide (201 attendu)"

    assert (
        member in structure.members.all()
    ), "L'utilisateur n'est pas membre de la structure"
    assert mock_create_contact.called, "Le contact Brevo n'a pas été créé"

    _, user, attrs, sib_list = mock_create_contact.call_args.args

    assert user == member, "L'utilisateur ne correspond pas"
    assert attrs, "Les attributs Brevo ne sont pas définis"
    assert str(sib_list) == expected_sib_list
