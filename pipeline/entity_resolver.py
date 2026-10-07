from typing import Dict, Any, List, Optional, Tuple
from pipeline.schema import CleanPerson, FactRegistration, generate_deterministic_person_uuid
from pipeline.name_parser import ParsedName

def jaro_winkler_similarity(s1: str, s2: str) -> float:
    """
    Standard Jaro-Winkler string distance metric for probabilistic record linkage.
    """
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

    len1, len2 = len(s1), len(s2)
    max_dist = max(len1, len2) // 2 - 1
    if max_dist < 0:
        max_dist = 0

    match1 = [False] * len1
    match2 = [False] * len2
    matches = 0

    for i in range(len1):
        start = max(0, i - max_dist)
        end = min(i + max_dist + 1, len2)
        for j in range(start, end):
            if not match2[j] and s1[i] == s2[j]:
                match1[i] = True
                match2[j] = True
                matches += 1
                break

    if matches == 0:
        return 0.0

    t = 0
    k = 0
    for i in range(len1):
        if match1[i]:
            while not match2[k]:
                k += 1
            if s1[i] != s2[k]:
                t += 1
            k += 1
    transpositions = t // 2

    m = matches
    jaro = (m / len1 + m / len2 + (m - transpositions) / m) / 3.0

    # Winkler prefix bonus (up to 4 characters, prefix scale p = 0.1)
    prefix = 0
    for i in range(min(len1, len2, 4)):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break

    return jaro + (prefix * 0.1 * (1.0 - jaro))

class HybridEntityResolver:
    """
    Hybrid Master Data Management (MDM) Entity Resolution Engine.
    Used internally strictly for entity linking, clustering, and deduplication:
    1. Fast deterministic indexing on canonical phone (E.164) and email.
    2. Probabilistic record linkage (Jaro-Winkler) on normalized name keys.
    3. Deterministic UUIDv5 generation for repeatable cluster IDs across batches.
    4. Survivorship merge rules (Information Completeness & Timestamp Recency).
    Note: Synthetic IDs are kept strictly internal and not forced onto final cleaned business datasets.
    """
    def __init__(self, name_similarity_threshold: float = 0.88):
        self.name_similarity_threshold = name_similarity_threshold
        
        # In-memory indices for resolved persons
        self.persons_by_id: Dict[str, CleanPerson] = {}
        self.phone_to_id: Dict[str, str] = {}
        self.email_to_id: Dict[str, str] = {}
        self.registrations: List[FactRegistration] = []
        
        # Deduplication tracking
        self.merged_duplicate_count: int = 0

    def resolve_person(
        self,
        phone_e164: Optional[str],
        email: Optional[str],
        parsed_name_ar: Optional[ParsedName],
        parsed_name_en: Optional[ParsedName],
        university: Optional[str] = None
    ) -> Tuple[CleanPerson, bool]:
        """
        Resolves or creates a Golden Person Entity.
        Returns (person, is_existing_duplicate).
        """
        matched_person_id: Optional[str] = None

        # -------------------------------------------------------------
        # Phase 1: Deterministic Match (Phone or Email)
        # -------------------------------------------------------------
        if phone_e164 and phone_e164 in self.phone_to_id:
            matched_person_id = self.phone_to_id[phone_e164]
        elif email and email in self.email_to_id:
            matched_person_id = self.email_to_id[email]

        # -------------------------------------------------------------
        # Phase 2: Probabilistic Match (Jaro-Winkler across names)
        # -------------------------------------------------------------
        if not matched_person_id:
            query_key_ar = (
                parsed_name_ar.normalized_key.casefold()
                if parsed_name_ar and parsed_name_ar.normalized_key
                else ""
            )

            query_key_en = (
                parsed_name_en.normalized_key.casefold()
                if parsed_name_en and parsed_name_en.normalized_key
                else ""
            )

            best_sim = 0.0
            best_cand_id = None

            for p_id, p in self.persons_by_id.items():
                cand_key_ar = (
                    p.full_name_ar.casefold()
                    if p.full_name_ar
                    else ""
                )

                cand_key_en = (
                    p.full_name_en.casefold()
                    if p.full_name_en
                    else ""
                )

                sim_ar = (
                    jaro_winkler_similarity(query_key_ar, cand_key_ar)
                    if query_key_ar and cand_key_ar
                    else 0.0
                )

                sim_en = (
                    jaro_winkler_similarity(query_key_en, cand_key_en)
                    if query_key_en and cand_key_en
                    else 0.0
                )

                max_name_sim = max(sim_ar, sim_en)

                if max_name_sim > best_sim:
                    best_sim = max_name_sim
                    best_cand_id = p_id

            if best_sim >= self.name_similarity_threshold:
                matched_person_id = best_cand_id

        # -------------------------------------------------------------
        # Phase 3: Survivorship & Merge
        # -------------------------------------------------------------
        if matched_person_id and matched_person_id in self.persons_by_id:
            existing_person = self.persons_by_id[matched_person_id]
            
            # Survivorship Rule: Completeness union
            if not existing_person.canonical_phone_e164 and phone_e164:
                existing_person.canonical_phone_e164 = phone_e164
                self.phone_to_id[phone_e164] = matched_person_id

            if not existing_person.canonical_email and email:
                existing_person.canonical_email = email
                self.email_to_id[email] = matched_person_id

            # Merge names: preserve Arabic and English representations
            if not existing_person.full_name_ar and parsed_name_ar and parsed_name_ar.full_clean:
                existing_person.full_name_ar = parsed_name_ar.full_clean
                existing_person.first_name = parsed_name_ar.first_name
                existing_person.father_name = parsed_name_ar.father_name
                existing_person.family_name = parsed_name_ar.family_name

            if not existing_person.full_name_en and parsed_name_en and parsed_name_en.full_clean:
                existing_person.full_name_en = parsed_name_en.full_clean
                if not existing_person.first_name:
                    existing_person.first_name = parsed_name_en.first_name
                    existing_person.father_name = parsed_name_en.father_name
                    existing_person.family_name = parsed_name_en.family_name

            return existing_person, True

        # -------------------------------------------------------------
        # Phase 4: Create New Golden Record with Deterministic UUIDv5
        # -------------------------------------------------------------
        primary_key = phone_e164 or email or (parsed_name_ar.full_clean if parsed_name_ar else (parsed_name_en.full_clean if parsed_name_en else "unknown"))
        new_person_id = generate_deterministic_person_uuid(primary_key)

        display_name = (
            (parsed_name_ar.full_clean if parsed_name_ar and parsed_name_ar.full_clean else None) or
            (parsed_name_en.full_clean if parsed_name_en and parsed_name_en.full_clean else None) or
            "Participant"
        )

        first_name = (parsed_name_ar.first_name if parsed_name_ar else None) or (parsed_name_en.first_name if parsed_name_en else None)
        father_name = (parsed_name_ar.father_name if parsed_name_ar else None) or (parsed_name_en.father_name if parsed_name_en else None)
        family_name = (parsed_name_ar.family_name if parsed_name_ar else None) or (parsed_name_en.family_name if parsed_name_en else None)

        person = CleanPerson(
            person_id=new_person_id,
            canonical_email=email,
            canonical_phone_e164=phone_e164,
            full_name_ar=parsed_name_ar.full_clean if parsed_name_ar else None,
            full_name_en=parsed_name_en.full_clean if parsed_name_en else None,
            first_name=first_name,
            father_name=father_name,
            family_name=family_name,
            clean_display_name=display_name
        )

        self.persons_by_id[new_person_id] = person
        if phone_e164:
            self.phone_to_id[phone_e164] = new_person_id
        if email:
            self.email_to_id[email] = new_person_id

        return person, False

    def add_registration_event(self, registration: FactRegistration):
        """
        Adds registration event applying duplicate survivorship.

        If the same person registered for the same dataset multiple times
        (within or across sheets):
        - Keeps latest timestamp.
        - Preserves positive attendance status.
        - Merges metadata.
        """

        existing_idx = None

        for i, reg in enumerate(self.registrations):
            if (
                reg.person_id == registration.person_id
                and reg.dataset_id == registration.dataset_id
            ):
                existing_idx = i
                break

        if existing_idx is not None:
            # Duplicate event detected. Apply survivorship.
            existing_reg = self.registrations[existing_idx]
            self.merged_duplicate_count += 1

            # Survivorship: Keep positive attendance
            if registration.attended_flag:
                existing_reg.attended_flag = True

            # Survivorship: Keep latest timestamp
            if registration.registered_at > existing_reg.registered_at:
                existing_reg.registered_at = registration.registered_at
                existing_reg.sheet_name = (
                    f"{existing_reg.sheet_name}, "
                    f"{registration.sheet_name}"
                )

            # Survivorship: Always merge metadata
            existing_reg.raw_metadata.update(
                registration.raw_metadata
            )

        else:
            self.registrations.append(registration)