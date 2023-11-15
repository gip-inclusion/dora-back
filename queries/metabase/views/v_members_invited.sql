-- membres d'une structure : 
-- invité en tant que membre de structure, validé ou non

DROP VIEW IF EXISTS v_members_invited;

CREATE OR REPLACE VIEW v_members_invited AS
SELECT 
mu.id "ID utilisateur", 
mu.email "E-mail", 
mu.date_joined "Date de création", 
mu.is_valid "Valide",
ms.name "Nom de la structure", 
ms.dora_url "URL Dora", 
ms.department "Département",
(SELECT count(*) > 0
 FROM structures_structuremember ssm 
 INNER JOIN mb_user mu2 ON ssm.user_id = mu2.id AND mu2.is_valid 
 WHERE is_admin AND structure_id = ms.id) "Structure avec admin actif",
ss.creation_date "Date d'invitation",
ss.is_admin "Invitation en tant qu'admin", 
ss.invited_by_admin "Invitation par un admin"
FROM mb_user mu 
INNER JOIN structures_structureputativemember ss ON mu.id = ss.user_id
LEFT JOIN mb_structure ms ON ms.id = ss.structure_id 
WHERE NOT mu.is_valid 
ORDER BY date_joined DESC;
