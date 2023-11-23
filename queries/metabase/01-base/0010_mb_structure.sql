drop table if exists mb_structure;

create table mb_structure as
select -- noqa: AM04
    structures_structure.*,
    (
        select concat('https://dora.inclusion.beta.gouv.fr/structures/', slug)
    ) as dora_url
from structures_structure;
