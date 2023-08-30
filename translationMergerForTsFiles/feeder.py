import os

def main():
    # Hardcoded mappings between 'target' and 'source' files
    mappings = {
        'cs_CZ': '230802_XBO_Automatikprogramme_cs_CZ-de-cs-QA-C.ts',
        'da_DK': '230802_XBO_Automatikprogramme_da_DK-de-da-QA-C.ts',
        'en_GB': '230802_XBO_Automatikprogramme_en_GB-de-en_gb-QA-C.ts',
        'es_ES': '230802_XBO_Automatikprogramme_es_ES-de-es-QA-C.ts',
        'et_EE': '230802_XBO_Automatikprogramme_et_EE-de-et_ee-QA-C.ts',
        'fi_FI': '230802_XBO_Automatikprogramme_fi_FI-de-fi_fi-QA-C.ts',
        'fr_FR': '230802_XBO_Automatikprogramme_fr_FR-de-fr-QA-C.ts',
        'it_IT': '230802_XBO_Automatikprogramme_it_IT-de-it-QA-C.ts',
        'nb_NO': '230802_XBO_Automatikprogramme_nb_NO-de-nb_no-QA-C.ts',
        'nl_NL': '230802_XBO_Automatikprogramme_nl_NL-de-nl_nl-QA-C.ts',
        'pl_PL': '230802_XBO_Automatikprogramme_pl_PL-de-pl-QA-C.ts',
        'pt_PT': '230802_XBO_Automatikprogramme_pt_PT-de-pt-QA-C.ts',
        'ro_RO': '230802_XBO_Automatikprogramme_ro_RO-de-ro-QA-C.ts',
        'sk_SK': '230802_XBO_Automatikprogramme_sk_SK-de-sk-QA-C.ts',
        'sl_SI': '230802_XBO_Automatikprogramme_sl_SI-de-sl-QA-C.ts',
        'sv_SE': '230802_XBO_Automatikprogramme_sv_SE-de-sv-QA-C.ts',
    }

    # Call the translationMerger.py script for each pair of 'target' and 'source' files
    for lang, source_file in mappings.items():
        target_file = f'recipebook_{lang}.ts'
        os.system(f'python translationMerger.py target={target_file} source={source_file}')

if __name__ == '__main__':
    main()
