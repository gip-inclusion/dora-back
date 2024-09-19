drop table if exists mb_stats_structureview;

create table mb_stats_structureview as
select
    search.id,
    search.path,
    search.date,
    search.anonymous_user_hash,
    search.is_logged,
    search.is_staff,
    search.is_manager,
    search.is_an_admin,
    search.user_kind,
    search.is_structure_member,
    search.is_structure_admin,
    search.structure_department,
    search.structure_city_code,
    search.structure_id,
    search.user_id,
    search.structure_source
from stats_structureview as search;

-- Keys & constraints
alter table mb_stats_structureview add primary key (id);

-- Indexes 
CREATE INDEX idx_mb_stats_structureview_date ON public.mb_stats_structureview USING btree ("date");
CREATE INDEX idx_mb_stats_structureview_filters ON public.mb_stats_structureview USING btree ("is_structure_member", "is_structure_admin", "is_staff");
CREATE INDEX idx_mb_stats_structureview_user_id ON public.mb_stats_structureview USING btree ("user_id");