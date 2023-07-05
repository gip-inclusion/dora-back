from typing import Optional


def make_di_service_data(
    id: str,
    source: str,
    code_insee: str,
    thematiques: Optional[list[str]] = None,
    types: Optional[list[str]] = None,
    frais: Optional[list[str]] = None,
    modes_accueil: Optional[list[str]] = None,
    zone_diffusion_type: Optional[str] = None,
    zone_diffusion_code: Optional[str] = None,
    date_maj: Optional[str] = "2023-01-01",
):
    return {
        "_di_geocodage_code_insee": None,
        "_di_geocodage_score": None,
        "id": id,
        "structure_id": "rouge-empire",
        "source": source,
        "nom": "Munoz",
        "presentation_resume": "Puissant fine.",
        "presentation_detail": "Épaule élever un.",
        "types": [] if types is None else types,
        "thematiques": [] if thematiques is None else thematiques,
        "prise_rdv": "https://teixeira.fr/",
        "frais": [] if frais is None else frais,
        "frais_autres": "Camarade il.",
        "profils": ["femmes", "jeunes-16-26"],
        "pre_requis": None,
        "cumulable": False,
        "justificatifs": None,
        "formulaire_en_ligne": None,
        "commune": "Sainte Jacquelineboeuf",
        "code_postal": "25454",
        "code_insee": code_insee,
        "adresse": "chemin de Ferreira",
        "complement_adresse": None,
        "longitude": -61.64115,
        "latitude": 9.8741475,
        "recurrence": None,
        "date_creation": "2022-01-01",
        "date_suspension": "2054-01-01",
        "lien_source": "https://dora.fr/cacher-violent",
        "telephone": "0102030405",
        "courriel": "xavierlaunay@example.org",
        "contact_public": False,
        "contact_nom_prenom": "David Rocher",
        "date_maj": date_maj,
        "modes_accueil": [] if modes_accueil is None else modes_accueil,
        "modes_orientation_accompagnateur": ["telephoner"],
        "modes_orientation_beneficiaire": ["telephoner"],
        "zone_diffusion_type": zone_diffusion_type,
        "zone_diffusion_code": zone_diffusion_code,
        "zone_diffusion_nom": "foo",
        "structure": {
            "nom": "Rouge Empire",
        },
    }


class FakeDataInclusionClient:
    def __init__(self, services: list[dict]) -> None:
        self.services = services

    def list_services(self, source: Optional[str] = None) -> list[dict]:
        raise NotImplementedError()

    def retrieve_service(self, source: str, id: str) -> Optional[dict]:
        raise NotImplementedError()

    def search_services(
        self,
        source: Optional[str] = None,
        code_insee: Optional[str] = None,
        thematiques: Optional[list[str]] = None,
        types: Optional[list[str]] = None,
        frais: Optional[list[str]] = None,
    ) -> list[dict]:
        services = self.services

        if source is not None:
            services = [r for r in services if r["source"] == source]

        if thematiques is not None:
            services = [
                r for r in services if any(t in r["thematiques"] for t in thematiques)
            ]

        if types is not None:
            services = [r for r in services if any(t in r["types"] for t in types)]

        if frais is not None:
            services = [r for r in services if any(t in r["frais"] for t in frais)]

        if code_insee is not None:
            return [
                # overly simple distance for tests. avoid corsica
                {"distance": abs(int(code_insee) - int(s["code_insee"])), "service": s}
                for s in services
            ]
        else:
            return [{"distance": None, "service": s} for s in services]
