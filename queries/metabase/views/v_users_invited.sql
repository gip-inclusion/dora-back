-- utilisateurs : 
-- membres d'une structure ou en attente, avec infos complémentaires

DROP VIEW IF EXISTS v_users_invited;

CREATE VIEW v_users_invited AS
SELECT 
id "ID utilisateur", 
email "E-mail", 
date_joined "Date de création",
mu.is_valid "Valide",
(SELECT ic_id IS not NULL) "Inscrit IC",
(SELECT date_joined < '2022-10-03') "Créé avant MEP IC",
(SELECT id IN (SELECT user_id FROM structures_structuremember ss)) "Membre d'une structure",
(SELECT id IN (SELECT user_id FROM structures_structureputativemember ss)) "En attente de rattachement"
FROM mb_user mu
WHERE not mu.is_staff 
ORDER by date_joined desc;
