def code_insee_to_code_dept(code_insee):
    return code_insee[:3] if code_insee.startswith("97") else code_insee[:2]
