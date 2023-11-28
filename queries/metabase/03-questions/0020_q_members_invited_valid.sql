-- Question : 
-- liste des membres invités, avec e-mail validé, en attente de validation 

-- noqa: disable=LT05

drop view if exists q_members_invited_valid;

create view q_members_invited_valid as
select
    "ID utilisateur",
    "E-mail",
    "E-mail validé",
    "Date de création",
    "Dernière connexion",
    "Nom de la structure",
    "URL Dora",
    "Département",
    "Date d'invitation",
    "Invitation en tant qu'admin",
    "Compte inactif",
    "Nombre d'admins dans la structure",
    "Premier admin de la structure",
    "Membre d'autres structures"
from mb_members_invited
where "E-mail validé";

comment on view q_members_invited_valid is 'Liste des membres invités en attente de validation : e-mail validé';
