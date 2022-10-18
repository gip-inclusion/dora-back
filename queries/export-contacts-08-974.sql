select distinct(s.contact_email) as email
from services_service s
         left join structures_structure st on s.structure_id = st.id
where s.status = 'PUBLISHED'
  and (st.department = '08' or st.department = '974')

union
select distinct(u.email) as email
from users_user u
         left join structures_structuremember m on u.id = m.user_id
         left join structures_structure st on m.structure_id = st.id
where (st.department = '08' or st.department = '974')
  and u.is_valid = true

union
select distinct(s.email) as email
from structures_structure s
where (s.department = '08' or s.department = '974')
order by email
