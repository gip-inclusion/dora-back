select all_emails.*
from ( with vars as ( select ? as department )
       select distinct(s.contact_email) as email
       from vars,
            services_service s
                left join structures_structure st on s.structure_id = st.id
       where s.status = 'PUBLISHED'
         and (st.department = vars.department)

       union
       select distinct(u.email) as email
       from vars,
            users_user u
                left join structures_structuremember m on u.id = m.user_id
                left join structures_structure st on m.structure_id = st.id
       where (st.department = vars.department)
         and u.is_valid = true

       union
       select distinct(s.email) as email
       from vars,
            structures_structure s
       where (s.department = vars.department) ) as all_emails
where not all_emails.email like '%@pole-emploi.%'
  and not all_emails.email = ''
order by all_emails.email;
