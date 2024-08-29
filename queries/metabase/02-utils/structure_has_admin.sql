create or replace function structure_has_admin(structure_id_input UUID)
returns BOOLEAN as $$
BEGIN
    RETURN (
        SELECT COUNT(*) > 0 AS has_admin
        FROM structures_structuremember
        LEFT JOIN users_user ON structures_structuremember.user_id = users_user.id
        WHERE structure_id = structure_id_input
        AND is_admin = true
        AND is_valid = true
        AND is_active = true
    );
END;
$$ language plpgsql;
